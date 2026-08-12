# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Daily on-hand snapshot.

A snapshot row freezes pallets-on-hand per (client, location) at a
moment in time. The cron creates one batch per night across all
clients; the billing engine sums snapshots over the period through
the client's storage_charging_basis.

Snapshots are immutable. Re-running the cron for a date that already
has snapshots raises rather than silently overwriting; back-fills
must use the explicit rebuild action which carries an audit log
entry.
"""
import logging
from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EhLogWarehouseSnapshot(models.Model):
    _name = "eh.log.warehouse.snapshot"
    _description = "Warehouse On-Hand Snapshot"
    _order = "snapshot_date desc, client_id, location_id"

    snapshot_date = fields.Date(
        string="Snapshot Date",
        required=True,
        index=True,
    )
    client_id = fields.Many2one(
        "eh.log.warehouse.client",
        string="3PL Client",
        required=True,
        ondelete="restrict",
        index=True,
    )
    facility_id = fields.Many2one(
        "eh.log.warehouse.facility",
        string="Facility",
        required=True,
        ondelete="restrict",
        index=True,
    )
    location_id = fields.Many2one(
        "eh.log.warehouse.location",
        string="Location",
        required=True,
        ondelete="restrict",
        index=True,
    )
    pallets_on_hand = fields.Integer(
        string="Pallets On Hand",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    _snapshot_unique = models.Constraint(
        'unique(snapshot_date, client_id, location_id)',
        'Duplicate snapshot for the same date / client / location.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_warehouse_internal_snapshot"):
            raise UserError(_(
                "[EHL-WHS-017] Snapshots are created by the daily "
                "cron or the explicit rebuild action; direct ORM "
                "creates are blocked."
            ))
        return super().create(vals_list)

    def write(self, vals):
        if self and not self.env.context.get("eh_log_warehouse_internal_snapshot"):
            raise UserError(_(
                "[EHL-WHS-018] Snapshots are immutable."
            ))
        return super().write(vals)

    def unlink(self):
        if self and not self.env.context.get("eh_log_warehouse_internal_snapshot"):
            raise UserError(_(
                "[EHL-WHS-019] Snapshots are append-only; use the "
                "rebuild action for back-fill."
            ))
        return super().unlink()

    # ------------------------------------------------------------------
    # Cron entry point
    # ------------------------------------------------------------------
    @api.model
    def cron_capture_daily_snapshot(self):
        """Capture one snapshot per (client, location) for yesterday.

        Runs nightly. Yesterday rather than today so day-end activity
        is fully reflected in the snapshot. Idempotent: rows already
        present for the target date are skipped (logged but not
        recreated) so a manual cron trigger does not corrupt history.
        """
        target_date = date.today() - timedelta(days=1)
        Movement = self.env["eh.log.warehouse.movement"]
        Client = self.env["eh.log.warehouse.client"].search([
            ("active", "=", True),
        ])
        cutoff = fields.Datetime.to_datetime(
            f"{target_date.isoformat()} 23:59:59"
        )
        Snapshot = self.with_context(eh_log_warehouse_internal_snapshot=True)
        created = 0
        for client in Client:
            inbound = Movement.read_group(
                domain=[
                    ("client_id", "=", client.id),
                    ("occurred_at", "<=", cutoff),
                    ("destination_location_id", "!=", False),
                ],
                fields=["destination_location_id", "pallet_count:sum"],
                groupby=["destination_location_id"],
            )
            outbound = Movement.read_group(
                domain=[
                    ("client_id", "=", client.id),
                    ("occurred_at", "<=", cutoff),
                    ("source_location_id", "!=", False),
                ],
                fields=["source_location_id", "pallet_count:sum"],
                groupby=["source_location_id"],
            )
            in_map = {
                row["destination_location_id"][0]: row["pallet_count"]
                for row in inbound if row.get("destination_location_id")
            }
            out_map = {
                row["source_location_id"][0]: row["pallet_count"]
                for row in outbound if row.get("source_location_id")
            }
            location_ids = set(in_map.keys()) | set(out_map.keys())
            for location_id in location_ids:
                on_hand = in_map.get(location_id, 0) - out_map.get(location_id, 0)
                if on_hand <= 0:
                    continue
                exists = self.search_count([
                    ("snapshot_date", "=", target_date),
                    ("client_id", "=", client.id),
                    ("location_id", "=", location_id),
                ])
                if exists:
                    continue
                location = self.env["eh.log.warehouse.location"].browse(location_id)
                Snapshot.create({
                    "snapshot_date": target_date,
                    "client_id": client.id,
                    "facility_id": location.facility_id.id,
                    "location_id": location_id,
                    "pallets_on_hand": on_hand,
                    "company_id": client.company_id.id,
                })
                created += 1
        _logger.info(
            "Daily warehouse snapshot for %s: %d row(s) created",
            target_date, created,
        )
        return created
