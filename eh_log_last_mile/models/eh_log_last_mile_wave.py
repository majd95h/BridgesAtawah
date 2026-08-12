# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Last-mile wave: one driver running many stops on a day.

Aggregates deliveries, exposes per-day operational counters, and
produces the driver manifest PDF.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


WAVE_STATES = [
    ("draft", "Draft"),
    ("dispatched", "Dispatched"),
    ("in_progress", "In Progress"),
    ("completed", "Completed"),
    ("closed", "Closed"),
    ("cancelled", "Cancelled"),
]

ALLOWED_WAVE_TRANSITIONS = {
    "draft": {"dispatched", "cancelled"},
    "dispatched": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


class EhLogLastMileWave(models.Model):
    _name = "eh.log.last.mile.wave"
    _description = "Last Mile Wave"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _order = "scheduled_date desc, id desc"
    _rec_names_search = ["name"]

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
        selection=WAVE_STATES,
        string="State",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_last_mile_wave_company_rel",
        "wave_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    # ----- Plan -----

    scheduled_date = fields.Date(
        string="Scheduled Date",
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )

    driver_id = fields.Many2one(
        "eh.log.transport.driver",
        string="Driver",
        required=True,
        index=True,
        tracking=True,
    )

    vehicle_id = fields.Many2one(
        "eh.log.transport.vehicle",
        string="Vehicle",
        required=True,
        index=True,
        tracking=True,
    )

    departed_at = fields.Datetime(string="Departed", readonly=True, copy=False, tracking=True)
    completed_at = fields.Datetime(string="Completed", readonly=True, copy=False, tracking=True)

    # ----- Deliveries -----

    delivery_ids = fields.One2many(
        "eh.log.last.mile.delivery",
        "wave_id",
        string="Deliveries",
    )

    delivery_count = fields.Integer(
        string="Stops",
        compute="_compute_aggregates",
        store=True,
    )

    delivered_count = fields.Integer(
        string="Delivered",
        compute="_compute_aggregates",
        store=True,
    )

    failed_count = fields.Integer(
        string="Failed",
        compute="_compute_aggregates",
        store=True,
    )

    pending_count = fields.Integer(
        string="Pending",
        compute="_compute_aggregates",
        store=True,
    )

    completion_pct = fields.Float(
        string="Completion (%)",
        compute="_compute_aggregates",
        store=True,
    )

    # ----- COD -----

    cod_expected = fields.Monetary(
        string="COD Expected",
        currency_field="currency_id",
        compute="_compute_aggregates",
        store=True,
    )

    cod_collected = fields.Monetary(
        string="COD Collected",
        currency_field="currency_id",
        compute="_compute_aggregates",
        store=True,
    )

    cod_outstanding = fields.Monetary(
        string="COD Outstanding",
        currency_field="currency_id",
        compute="_compute_aggregates",
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
        store=True,
    )

    notes = fields.Text(string="Notes")

    # ----- Computes -----

    @api.depends("company_id")
    def _compute_company_ids(self):
        for wave in self:
            wave.company_ids = wave.company_id

    @api.depends(
        "delivery_ids",
        "delivery_ids.state",
        "delivery_ids.cod_amount",
        "delivery_ids.cod_collected_amount",
    )
    def _compute_aggregates(self):
        for wave in self:
            deliveries = wave.delivery_ids
            wave.delivery_count = len(deliveries)
            wave.delivered_count = len(deliveries.filtered(
                lambda d: d.state == "delivered"
            ))
            wave.failed_count = len(deliveries.filtered(
                lambda d: d.state in ("failed", "returned")
            ))
            wave.pending_count = len(deliveries.filtered(
                lambda d: d.state in ("scheduled", "out_for_delivery")
            ))
            wave.completion_pct = (
                (wave.delivered_count / wave.delivery_count) * 100.0
                if wave.delivery_count else 0.0
            )
            wave.cod_expected = sum(deliveries.mapped("cod_amount"))
            wave.cod_collected = sum(deliveries.mapped("cod_collected_amount"))
            wave.cod_outstanding = wave.cod_expected - wave.cod_collected

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.last.mile.wave"
                ) or _("New")
        return super().create(vals_list)

    def _transition_state(self, target_state: str):
        for wave in self:
            current = wave.state
            allowed = ALLOWED_WAVE_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    150,
                    _(
                        "Wave %(name)s cannot move from %(current)s to "
                        "%(target)s. Allowed transitions from "
                        "%(current)s: %(allowed)s."
                    ) % {
                        "name": wave.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            wave.with_context(eh_log_last_mile_wave_state_write=True).write({
                "state": target_state,
            })

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_last_mile_wave_state_write"):
            raise UserError(_(
                "[EHL-LM-WAVE-001] State changes on a wave must go "
                "through the action buttons. Direct writes are rejected."
            ))
        return super().write(vals)

    # ----- Pre-flight -----

    def _check_dispatch_prerequisites(self):
        for wave in self:
            blockers = []
            if not wave.delivery_ids:
                blockers.append(_("Wave has no scheduled deliveries."))
            if wave.driver_id and wave.driver_id.is_license_expired:
                blockers.append(_(
                    "Driver %(driver)s has an expired license "
                    "(expired %(date)s)."
                ) % {
                    "driver": wave.driver_id.name,
                    "date": wave.driver_id.license_expiry_date,
                })
            if blockers:
                raise UserError(_(
                    "[EHL-LM-WAVE-002] Wave %(name)s cannot be "
                    "dispatched. Resolve:\n\n- %(list)s"
                ) % {
                    "name": wave.name,
                    "list": "\n- ".join(blockers),
                })

    # ----- Actions -----

    def action_dispatch(self):
        self._check_dispatch_prerequisites()
        self._transition_state("dispatched")
        for wave in self:
            wave.departed_at = fields.Datetime.now()
            # Move all scheduled deliveries to out_for_delivery.
            for delivery in wave.delivery_ids.filtered(
                lambda d: d.state == "scheduled"
            ):
                delivery.action_set_out_for_delivery()
        return True

    def action_set_in_progress(self):
        self._transition_state("in_progress")
        return True

    def action_complete(self):
        for wave in self:
            if wave.pending_count:
                raise UserError(_(
                    "[EHL-LM-WAVE-003] Wave %(name)s has %(count)d "
                    "pending deliveries. Resolve every stop (deliver, "
                    "fail, or return) before completion."
                ) % {"name": wave.name, "count": wave.pending_count})
            wave._transition_state("completed")
            wave.completed_at = fields.Datetime.now()
        return True

    def action_close(self):
        for wave in self:
            if wave.cod_outstanding > 0:
                raise UserError(_(
                    "[EHL-LM-WAVE-004] Wave %(name)s cannot be closed "
                    "while COD outstanding is %(amount)s. Settle the "
                    "outstanding amount first."
                ) % {"name": wave.name, "amount": wave.cod_outstanding})
            wave._transition_state("closed")
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True

    def action_view_deliveries(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Deliveries"),
            "res_model": "eh.log.last.mile.delivery",
            "view_mode": "list,form",
            "domain": [("wave_id", "=", self.id)],
            "context": {"default_wave_id": self.id},
        }
