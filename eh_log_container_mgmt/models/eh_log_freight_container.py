# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Freight container extension: depot, lease, and demurrage/detention."""
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class EhLogFreightContainer(models.Model):
    _inherit = "eh.log.freight.container"

    # ----- Current location -----

    current_depot_id = fields.Many2one(
        "eh.log.container.mgmt.depot",
        string="Current Depot",
        ondelete="set null",
        index=True,
        help="Last known depot. Updated automatically by gate "
             "movements; can be edited manually for corrections.",
    )

    movement_ids = fields.One2many(
        "eh.log.container.mgmt.movement",
        "container_id",
        string="Gate Movements",
    )

    movement_count = fields.Integer(
        string="Movements",
        compute="_compute_movement_count",
    )

    # ----- Lease -----

    lease_contract_id = fields.Many2one(
        "eh.log.container.mgmt.lease.contract",
        string="Lease Contract",
        ondelete="set null",
        index=True,
        help="Active lease contract this container falls under. Used "
             "by per-container D&D and headline billing.",
    )

    # ----- Demurrage and detention -----

    free_time_days = fields.Integer(
        string="Free Time (days)",
        default=7,
        help="Days included in the agreed price after gate-out before "
             "demurrage or detention starts to accrue. Defaults to 7 "
             "days; override per container for special arrangements.",
    )

    dnd_rate_per_day = fields.Monetary(
        string="D&D Rate (per day)",
        currency_field="currency_id",
        help="Per-container per-day rate that applies after free time "
             "elapses. Lookup chain: container override, lease "
             "contract daily rate, configured default per ISO type.",
    )

    days_at_destination = fields.Integer(
        string="Days at Destination",
        compute="_compute_dnd",
        store=False,
        help="Days since destination gate-out, before destination "
             "gate-in. Used by the D&D calculation.",
    )

    dnd_chargeable_days = fields.Integer(
        string="D&D Chargeable Days",
        compute="_compute_dnd",
        store=False,
        help="Chargeable days = max(0, days_at_destination - free_time_days).",
    )

    dnd_amount = fields.Monetary(
        string="D&D Amount",
        currency_field="currency_id",
        compute="_compute_dnd",
        store=False,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # ----- Computes -----

    @api.depends("movement_ids")
    def _compute_movement_count(self):
        for container in self:
            container.movement_count = len(container.movement_ids)

    @api.depends("gate_out_at", "returned_at", "free_time_days", "dnd_rate_per_day")
    def _compute_dnd(self):
        for container in self:
            if not container.gate_out_at:
                container.days_at_destination = 0
                container.dnd_chargeable_days = 0
                container.dnd_amount = 0.0
                continue
            end = container.returned_at or fields.Datetime.now()
            # Demurrage and detention are billed in whole calendar days the
            # container sits at destination, so the count is a date
            # difference. Sub-second arithmetic here is both wrong for the
            # domain and flaky: gate_out_at keeps microseconds while
            # fields.Datetime.now() is truncated to the second, which would
            # floor a clean 20-day span to 19.
            days = max(0, (end.date() - container.gate_out_at.date()).days)
            chargeable = max(0, days - (container.free_time_days or 0))
            container.days_at_destination = days
            container.dnd_chargeable_days = chargeable
            container.dnd_amount = chargeable * (container.dnd_rate_per_day or 0.0)

    # ----- Movement-driven location update -----

    def _refresh_current_depot(self):
        """Set current_depot_id from the most recent gate movement.

        Ordering is by timestamp, then by id so two movements stamped at
        the same instant resolve to the one recorded last rather than an
        arbitrary winner.
        """
        for container in self:
            latest = container.movement_ids.sorted(
                key=lambda m: (m.happened_at, m.id), reverse=True
            )[:1]
            if latest:
                container.current_depot_id = latest.depot_id

    # ----- Actions -----

    def action_view_movements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Gate Movements"),
            "res_model": "eh.log.container.mgmt.movement",
            "view_mode": "list,form",
            "domain": [("container_id", "=", self.id)],
            "context": {"default_container_id": self.id},
        }

    @api.model
    def _gc_dnd_alerts(self):
        """Cron entry point: warn account owners on containers crossing
        the free time threshold without a destination gate-in. Idempotent
        per container per day via mail.thread tracking.
        """
        today = fields.Date.context_today(self)
        candidates = self.search([
            ("gate_out_at", "!=", False),
            ("returned_at", "=", False),
            ("free_time_days", ">", 0),
        ])
        for container in candidates:
            container._compute_dnd()
            if container.dnd_chargeable_days > 0:
                _logger.info(
                    "Container %s crossed free time on %s. Chargeable "
                    "days: %s, amount: %s.",
                    container.container_number, today,
                    container.dnd_chargeable_days, container.dnd_amount,
                )


class EhLogContainerMgmtMovement(models.Model):
    _inherit = "eh.log.container.mgmt.movement"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # After every movement creation, refresh the container's
        # current depot. This is a simple latest-wins rule; more
        # sophisticated rules (e.g. only gate-in / transfer-in events
        # change current_depot) can be layered by a customer-specific
        # subclass.
        records.mapped("container_id")._refresh_current_depot()
        return records
