# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Deviation event.

Created automatically by the deviation detector when readings breach
the profile thresholds for longer than the alert window. Carries a
resolution workflow: open, acknowledged, resolved, voided. The
``cargo_impacting`` flag drives the compliance verdict.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


DEVIATION_STATES = [
    ("open", "Open"),
    ("acknowledged", "Acknowledged"),
    ("resolved", "Resolved"),
    ("voided", "Voided (False Alarm)"),
]

ALLOWED_DEVIATION_TRANSITIONS = {
    "open": {"acknowledged", "voided"},
    "acknowledged": {"resolved", "voided"},
    "resolved": set(),
    "voided": set(),
}

DEVIATION_KINDS = [
    ("high", "Above Maximum"),
    ("low", "Below Minimum"),
]

DEVIATION_CAUSES = [
    ("equipment_failure", "Equipment Failure"),
    ("door_open", "Door Open Too Long"),
    ("loading_unloading", "Loading or Unloading"),
    ("ambient_extreme", "Ambient Conditions"),
    ("logger_calibration", "Logger Calibration Drift"),
    ("transit_delay", "Transit Delay"),
    ("operator_error", "Operator Error"),
    ("other", "Other"),
]


class EhLogColdChainDeviation(models.Model):
    _name = "eh.log.cold.chain.deviation"
    _description = "Cold Chain Deviation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "started_at desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Reference",
        compute="_compute_name",
        store=True,
        index=True,
    )

    run_id = fields.Many2one(
        "eh.log.cold.chain.run",
        string="Run",
        required=True,
        ondelete="cascade",
        index=True,
    )

    state = fields.Selection(
        selection=DEVIATION_STATES,
        string="State",
        default="open",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    deviation_kind = fields.Selection(
        selection=DEVIATION_KINDS,
        string="Kind",
        required=True,
        index=True,
    )

    started_at = fields.Datetime(
        string="Started",
        required=True,
        index=True,
        tracking=True,
    )

    ended_at = fields.Datetime(
        string="Ended",
        index=True,
        tracking=True,
    )

    duration_minutes = fields.Float(
        string="Duration (min)",
        compute="_compute_duration",
        store=True,
    )

    min_temperature = fields.Float(
        string="Minimum Recorded (degC)",
        digits=(6, 2),
    )

    max_temperature = fields.Float(
        string="Maximum Recorded (degC)",
        digits=(6, 2),
    )

    cargo_impacting = fields.Boolean(
        string="Cargo Impacting",
        default=False,
        tracking=True,
        help="When True, the deviation is judged to have impacted the "
             "cargo's integrity. This drives the run's compliance "
             "verdict and the certificate's verdict line.",
    )

    cause = fields.Selection(
        selection=DEVIATION_CAUSES,
        string="Cause",
        tracking=True,
    )

    resolution_notes = fields.Text(string="Resolution Notes")

    acknowledged_by_id = fields.Many2one(
        "res.users",
        string="Acknowledged By",
        readonly=True,
        copy=False,
    )

    acknowledged_at = fields.Datetime(
        string="Acknowledged At",
        readonly=True,
        copy=False,
    )

    resolved_by_id = fields.Many2one(
        "res.users",
        string="Resolved By",
        readonly=True,
        copy=False,
    )

    resolved_at = fields.Datetime(
        string="Resolved At",
        readonly=True,
        copy=False,
    )

    company_id = fields.Many2one(
        related="run_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("run_id", "started_at", "deviation_kind")
    def _compute_name(self):
        for record in self:
            run_name = record.run_id.name or "?"
            ts = record.started_at and record.started_at.strftime("%Y%m%d-%H%M") or "?"
            kind = (record.deviation_kind or "?").upper()
            record.name = f"{run_name}/DEV-{kind}-{ts}"

    @api.depends("started_at", "ended_at")
    def _compute_duration(self):
        for record in self:
            if record.started_at and record.ended_at:
                delta = record.ended_at - record.started_at
                record.duration_minutes = delta.total_seconds() / 60.0
            else:
                record.duration_minutes = 0.0

    def _transition_state(self, target_state: str):
        for record in self:
            current = record.state
            allowed = ALLOWED_DEVIATION_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    123,
                    _(
                        "Deviation %(name)s cannot move from %(current)s "
                        "to %(target)s. Allowed transitions: %(allowed)s."
                    ) % {
                        "name": record.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            record.with_context(eh_log_cold_chain_dev_state_write=True).write({
                "state": target_state,
            })

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_cold_chain_dev_state_write"):
            raise UserError(_(
                "[EHL-COLD-CHAIN-DEV-001] State changes on a cold "
                "chain deviation must go through the action buttons. "
                "Direct writes are rejected."
            ))
        return super().write(vals)

    def action_acknowledge(self):
        for record in self:
            record._transition_state("acknowledged")
            record.acknowledged_by_id = self.env.user
            record.acknowledged_at = fields.Datetime.now()
        return True

    def action_resolve(self):
        for record in self:
            if not record.cause:
                raise UserError(_(
                    "[EHL-COLD-CHAIN-DEV-002] Deviation %(name)s "
                    "cannot be resolved without a cause classification."
                ) % {"name": record.name})
            record._transition_state("resolved")
            record.resolved_by_id = self.env.user
            record.resolved_at = fields.Datetime.now()
        return True

    def action_void(self):
        for record in self:
            if not record.resolution_notes:
                raise UserError(_(
                    "[EHL-COLD-CHAIN-DEV-003] Voiding deviation "
                    "%(name)s requires a justification in the "
                    "resolution notes."
                ) % {"name": record.name})
            record._transition_state("voided")
        return True

    def action_mark_cargo_impacting(self):
        for record in self:
            record.cargo_impacting = True
            record.message_post(body=_(
                "Deviation flagged as cargo-impacting by %(user)s. The "
                "run's compliance verdict is now non-compliant."
            ) % {"user": self.env.user.display_name})
        return True
