# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Disbursement Account (DA) and lines.

The DA is the financial spine of a port call: estimate first
(proforma issued to the principal before arrival), actuals appended
throughout the call, posted to a sale order on close, and settled
when payment is received.

State machine:

    draft -> proforma -> actual -> posted -> settled
                                    \-> cancelled

Estimate lines (is_estimate=True) capture the proforma; actual lines
record real disbursements with supporting documents. The variance
between estimate and actual is the agency's exposure on the call;
the report renders both columns side by side.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "draft":     ("proforma", "cancelled"),
    "proforma":  ("actual", "cancelled"),
    "actual":    ("posted", "cancelled"),
    "posted":    ("settled",),
    "settled":   (),
    "cancelled": (),
}


class EhLogShipDisbursementAccount(models.Model):
    _name = "eh.log.ship.disbursement.account"
    _description = "Disbursement Account"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("proforma", "Proforma Issued"),
            ("actual", "Actuals Recorded"),
            ("posted", "Posted to Sale Order"),
            ("settled", "Settled"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    port_call_id = fields.Many2one(
        "eh.log.ship.port.call",
        string="Port Call",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    vessel_id = fields.Many2one(
        related="port_call_id.vessel_id",
        store=True,
        readonly=True,
    )
    principal_partner_id = fields.Many2one(
        "res.partner",
        string="Principal",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "eh.log.ship.disbursement.line",
        "account_id",
        string="Lines",
    )
    estimate_total = fields.Monetary(
        string="Estimate Total",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    actual_total = fields.Monetary(
        string="Actual Total",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    variance = fields.Monetary(
        string="Variance",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
        help="Actual minus estimate. Positive = over-budget.",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Posted Sale Order",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.ship.disbursement.account"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("line_ids.amount", "line_ids.is_estimate")
    def _compute_totals(self):
        for account in self:
            estimate = sum(
                line.amount for line in account.line_ids if line.is_estimate
            )
            actual = sum(
                line.amount for line in account.line_ids if not line.is_estimate
            )
            account.estimate_total = estimate
            account.actual_total = actual
            account.variance = actual - estimate

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for account in self:
            current = account.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Disbursement account %(name)s cannot move "
                      "from %(from)s to %(to)s.") % {
                        "name": account.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            account.with_context(
                eh_log_ship_internal_state_write=True
            ).write({"state": target_state})

    def action_issue_proforma(self):
        for account in self:
            if not account.line_ids.filtered(lambda l: l.is_estimate):
                raise UserError(_(
                    "[EHL-SHP-012] Disbursement account %(name)s "
                    "has no estimate lines; add at least one "
                    "before issuing the proforma."
                ) % {"name": account.name})
        self._transition_state("proforma")

    def action_record_actuals(self):
        self._transition_state("actual")

    def action_post(self):
        for account in self:
            if not account.line_ids:
                raise UserError(_(
                    "[EHL-SHP-013] Disbursement account %(name)s "
                    "has no lines."
                ) % {"name": account.name})
            order = account._create_sale_order()
            account.sale_order_id = order.id
        self._transition_state("posted")

    def action_mark_settled(self):
        self._transition_state("settled")

    def action_cancel(self):
        self._transition_state("cancelled")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_ship_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-SHP-014] Disbursement-account state must "
                "change via the action buttons."
            ))
        return super().write(vals)

    def _create_sale_order(self):
        self.ensure_one()
        Order = self.env["sale.order"]
        order = Order.create({
            "partner_id": self.principal_partner_id.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "client_order_ref": self.name,
            "eh_log_ship_disbursement_account_id": self.id,
        })
        for line in self.line_ids.filtered(lambda l: not l.is_estimate):
            self.env["sale.order.line"].with_context(eh_log_force_charge_product=True).create({
                "order_id": order.id,
                "name": line.description or (
                    line.husbandry_service_id.name
                    or line.charge_code_id.name
                    or _("Disbursement")
                ),
                "product_uom_qty": 1.0,
                "price_unit": line.amount,
            })
        return order


class EhLogShipDisbursementLine(models.Model):
    _name = "eh.log.ship.disbursement.line"
    _description = "Disbursement Line"
    _order = "account_id, sequence, id"

    account_id = fields.Many2one(
        "eh.log.ship.disbursement.account",
        string="Disbursement Account",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Char(string="Description", required=True)
    is_estimate = fields.Boolean(
        string="Estimate",
        default=False,
        help=(
            "Tick to mark this line as part of the proforma "
            "estimate. Untick for actual disbursements."
        ),
    )
    charge_code_id = fields.Many2one(
        "eh.log.charge.code",
        string="Charge Code",
        ondelete="restrict",
    )
    husbandry_service_id = fields.Many2one(
        "eh.log.ship.husbandry.service",
        string="Husbandry Service",
        ondelete="restrict",
        help=(
            "Optional. When set, the default charge code is copied "
            "from the husbandry catalog at line creation."
        ),
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="account_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="account_id.company_id",
        store=True,
        index=True,
    )

    @api.onchange("husbandry_service_id")
    def _onchange_husbandry_service(self):
        if self.husbandry_service_id and not self.charge_code_id:
            self.charge_code_id = self.husbandry_service_id.charge_code_id

    def write(self, vals):
        for line in self:
            if line.account_id.state in ("posted", "settled", "cancelled"):
                raise UserError(_(
                    "[EHL-SHP-015] Disbursement account %(name)s is "
                    "%(state)s; lines are read-only."
                ) % {
                    "name": line.account_id.name,
                    "state": line.account_id.state,
                })
        return super().write(vals)
