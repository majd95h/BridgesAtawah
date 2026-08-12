# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Container lease contract.

Two directions:

* Lease-in: the broker holds containers from a vendor. Daily cost
  per container; we owe.
* Lease-out: the broker offers fleet to a customer. Daily revenue
  per container; we receive.

Each contract carries a fleet count, daily rate, term, and a free-day
allowance for incidental returns.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


CONTRACT_DIRECTIONS = [
    ("lease_in", "Lease-In (vendor to us)"),
    ("lease_out", "Lease-Out (us to customer)"),
]


CONTRACT_STATES = [
    ("draft", "Draft"),
    ("active", "Active"),
    ("expired", "Expired"),
    ("cancelled", "Cancelled"),
]


ALLOWED_CONTRACT_TRANSITIONS = {
    "draft": {"active", "cancelled"},
    "active": {"expired", "cancelled"},
    "expired": set(),
    "cancelled": set(),
}


class EhLogContainerMgmtLeaseContract(models.Model):
    _name = "eh.log.container.mgmt.lease.contract"
    _description = "Container Lease Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _rec_names_search = ["name", "partner_reference"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )

    state = fields.Selection(
        selection=CONTRACT_STATES,
        string="State",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    direction = fields.Selection(
        selection=CONTRACT_DIRECTIONS,
        string="Direction",
        required=True,
        index=True,
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Counterparty",
        required=True,
        index=True,
        tracking=True,
        help="Vendor on lease-in, customer on lease-out.",
    )

    partner_reference = fields.Char(string="Counterparty Reference", tracking=True)

    iso_type_id = fields.Many2one(
        "eh.log.freight.container.iso.type",
        string="ISO Type",
        required=True,
        ondelete="restrict",
        index=True,
        help="Container type covered by this contract. Mixed-type "
             "fleet is modelled as multiple contracts.",
    )

    fleet_count = fields.Integer(
        string="Fleet Count",
        required=True,
        default=1,
        help="Number of containers covered. Used for headline pricing "
             "and reporting; per-container assignment lives on the "
             "container record (lease_contract_id).",
    )

    daily_rate = fields.Monetary(
        string="Daily Rate (per container)",
        currency_field="currency_id",
        required=True,
    )

    free_days = fields.Integer(
        string="Free Days (per container)",
        default=0,
        help="Days for which the daily rate is waived per container "
             "movement cycle. Useful for short-turn lease-out arrangements.",
    )

    starts_on = fields.Date(string="Starts On", required=True, tracking=True)
    ends_on = fields.Date(string="Ends On", required=True, tracking=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_container_mgmt_lease_company_rel",
        "contract_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    container_ids = fields.One2many(
        "eh.log.freight.container",
        "lease_contract_id",
        string="Containers",
    )

    container_count = fields.Integer(
        string="Containers Assigned",
        compute="_compute_container_count",
    )

    days_total = fields.Integer(
        string="Term (days)",
        compute="_compute_days_total",
        store=True,
    )

    headline_value = fields.Monetary(
        string="Headline Value",
        currency_field="currency_id",
        compute="_compute_headline_value",
        store=True,
        help="Fleet count * daily rate * term days. Indicative "
             "headline only; actual billing reflects per-container "
             "free-day usage.",
    )

    notes = fields.Text(string="Notes")

    # ----- Computes -----

    @api.depends("company_id")
    def _compute_company_ids(self):
        for record in self:
            record.company_ids = record.company_id

    @api.depends("container_ids")
    def _compute_container_count(self):
        for record in self:
            record.container_count = len(record.container_ids)

    @api.depends("starts_on", "ends_on")
    def _compute_days_total(self):
        for record in self:
            if record.starts_on and record.ends_on and record.ends_on >= record.starts_on:
                record.days_total = (record.ends_on - record.starts_on).days + 1
            else:
                record.days_total = 0

    @api.depends("fleet_count", "daily_rate", "days_total")
    def _compute_headline_value(self):
        for record in self:
            record.headline_value = (
                (record.fleet_count or 0)
                * (record.daily_rate or 0.0)
                * (record.days_total or 0)
            )

    @api.constrains("starts_on", "ends_on")
    def _check_term(self):
        for record in self:
            if record.ends_on < record.starts_on:
                raise UserError(_(
                    "[EHL-CTNR-LEASE-001] Contract %(name)s end date "
                    "is before start date."
                ) % {"name": record.name})

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.container.mgmt.lease.contract"
                ) or _("New")
        return super().create(vals_list)

    def _transition_state(self, target_state: str):
        for record in self:
            current = record.state
            allowed = ALLOWED_CONTRACT_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    141,
                    _(
                        "Lease contract %(name)s cannot move from "
                        "%(current)s to %(target)s. Allowed transitions "
                        "from %(current)s: %(allowed)s."
                    ) % {
                        "name": record.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            record.with_context(eh_log_container_mgmt_lease_state_write=True).write({
                "state": target_state,
            })

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_container_mgmt_lease_state_write"):
            raise UserError(_(
                "[EHL-CTNR-LEASE-002] State changes on a lease "
                "contract must go through the action buttons. Direct "
                "writes are rejected."
            ))
        return super().write(vals)

    def action_activate(self):
        self._transition_state("active")
        return True

    def action_expire(self):
        self._transition_state("expired")
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True
