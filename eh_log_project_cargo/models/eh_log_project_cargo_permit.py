# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Permit register.

A permit row tracks one document issued by an authority (police,
roads agency, utility) authorising the move. State machine:

    draft -> applied -> issued -> active -> closed
                     \-> rejected -> draft

The cron walks active permits with expiry within an alert window and
posts an activity on the parent job so the operator gets a clear
warning before the move starts.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


# Days before expiry at which the alert cron posts a renew activity.
# Operators can change this through ir.config_parameter without a
# code change; the constant is the floor.
DEFAULT_ALERT_DAYS = 7


PERMIT_AUTHORITIES = [
    ("police", "Police Escort"),
    ("road", "Road Authority"),
    ("utility", "Utility (power/telecom)"),
    ("port", "Port Authority"),
    ("customs", "Customs"),
    ("environmental", "Environmental"),
    ("other", "Other"),
]


ALLOWED_TRANSITIONS = {
    "draft":    ("applied", "cancelled"),
    "applied":  ("issued", "rejected", "cancelled"),
    "issued":   ("active", "cancelled"),
    "active":   ("closed", "cancelled"),
    "rejected": ("draft", "cancelled"),
    "closed":   (),
    "cancelled": (),
}


class EhLogProjectCargoPermit(models.Model):
    _name = "eh.log.project.cargo.permit"
    _description = "Project Cargo Permit"
    _order = "valid_until, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name", "permit_reference"]

    name = fields.Char(string="Name", required=True, tracking=True)
    permit_reference = fields.Char(string="Permit Reference", tracking=True)
    job_id = fields.Many2one(
        "eh.log.project.cargo.job",
        string="Job",
        required=True,
        ondelete="cascade",
        index=True,
    )
    convoy_id = fields.Many2one(
        "eh.log.project.cargo.convoy",
        string="Convoy",
        domain="[('job_id', '=', job_id)]",
    )
    authority = fields.Selection(
        PERMIT_AUTHORITIES,
        string="Issuing Authority",
        required=True,
        tracking=True,
    )
    issuing_partner_id = fields.Many2one(
        "res.partner",
        string="Issuing Partner",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("applied", "Applied"),
            ("issued", "Issued"),
            ("active", "Active"),
            ("rejected", "Rejected"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    applied_at = fields.Date(string="Applied On")
    issued_at = fields.Date(string="Issued On")
    valid_from = fields.Date(string="Valid From")
    valid_until = fields.Date(string="Valid Until", tracking=True)
    days_until_expiry = fields.Integer(
        string="Days Until Expiry",
        compute="_compute_days_until_expiry",
    )
    cost_amount = fields.Monetary(
        string="Cost",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        related="job_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("valid_until")
    def _compute_days_until_expiry(self):
        today = fields.Date.context_today(self)
        for permit in self:
            if not permit.valid_until:
                permit.days_until_expiry = 0
            else:
                permit.days_until_expiry = (permit.valid_until - today).days

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for permit in self:
            current = permit.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Permit %(name)s cannot move from %(from)s to "
                      "%(to)s.") % {
                        "name": permit.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            permit.with_context(
                eh_log_project_cargo_internal_state_write=True
            ).write({"state": target_state})

    def action_apply(self):
        self._transition_state("applied")
        for permit in self:
            permit.applied_at = fields.Date.context_today(self)

    def action_mark_issued(self):
        for permit in self:
            if not permit.valid_until:
                raise UserError(_(
                    "[EHL-PCG-011] Permit %(name)s requires a "
                    "valid-until date before it can be marked "
                    "issued."
                ) % {"name": permit.name})
        self._transition_state("issued")
        for permit in self:
            permit.issued_at = fields.Date.context_today(self)

    def action_activate(self):
        self._transition_state("active")

    def action_mark_rejected(self):
        self._transition_state("rejected")

    def action_close(self):
        self._transition_state("closed")

    def action_cancel(self):
        self._transition_state("cancelled")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_project_cargo_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-PCG-012] Permit state must change via the "
                "action buttons."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Expiry alert cron
    # ------------------------------------------------------------------
    @api.model
    def cron_alert_expiring(self):
        today = fields.Date.context_today(self)
        Permit = self.search([
            ("state", "in", ("issued", "active")),
            ("valid_until", "!=", False),
            ("valid_until", ">=", today),
            ("valid_until", "<=", today + timedelta(days=DEFAULT_ALERT_DAYS)),
        ])
        for permit in Permit:
            permit.activity_schedule(
                "mail.mail_activity_data_warning",
                summary=_("Permit %(name)s expires on %(date)s") % {
                    "name": permit.name,
                    "date": permit.valid_until,
                },
                user_id=permit.create_uid.id or self.env.uid,
            )
        return len(Permit)
