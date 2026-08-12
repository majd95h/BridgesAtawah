# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Time-series temperature reading.

Append-only at the API level (writes to existing rows are restricted).
Designed to scale to one hundred thousand rows per run with proper
indexing.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


READING_SOURCES = [
    ("manual", "Manual Entry"),
    ("ingest", "Bulk Ingest"),
    ("telematics", "Telematics Stream"),
    ("portal", "Customer Portal"),
    ("api", "API"),
]


class EhLogColdChainReading(models.Model):
    _name = "eh.log.cold.chain.reading"
    _description = "Cold Chain Reading"
    _order = "captured_at desc, id desc"
    _rec_name = "captured_at"

    run_id = fields.Many2one(
        "eh.log.cold.chain.run",
        string="Run",
        required=True,
        ondelete="cascade",
        index=True,
    )

    captured_at = fields.Datetime(
        string="Captured At",
        required=True,
        index=True,
    )

    temperature = fields.Float(
        string="Temperature (degC)",
        required=True,
        digits=(6, 2),
    )

    humidity = fields.Float(
        string="Humidity (%)",
        digits=(5, 2),
    )

    source = fields.Selection(
        selection=READING_SOURCES,
        string="Source",
        default="manual",
        required=True,
        index=True,
    )

    sensor_reference = fields.Char(
        string="Sensor Reference",
        help="Optional identifier for the source sensor or logger. "
             "Useful when multiple sensors feed into the same run.",
    )

    company_id = fields.Many2one(
        related="run_id.company_id",
        store=True,
        index=True,
    )

    is_breach = fields.Boolean(
        string="Breach",
        compute="_compute_is_breach",
        store=True,
        help="True when this individual reading is outside the run's "
             "profile thresholds. The deviation detector aggregates "
             "sustained breaches across continuous time windows.",
    )

    @api.depends(
        "temperature",
        "run_id.profile_id.temperature_min",
        "run_id.profile_id.temperature_max",
    )
    def _compute_is_breach(self):
        for reading in self:
            profile = reading.run_id.profile_id
            if not profile:
                reading.is_breach = False
                continue
            reading.is_breach = (
                reading.temperature < profile.temperature_min
                or reading.temperature > profile.temperature_max
            )

    def write(self, vals):
        if not self.env.context.get("eh_log_cold_chain_internal_reading_write"):
            forbidden = set(vals) - {"sensor_reference", "source"}
            if forbidden:
                raise UserError(_(
                    "[EHL-COLD-CHAIN-READING-001] Cold chain readings "
                    "are append-only. The following fields cannot be "
                    "edited after capture: %(fields)s."
                ) % {"fields": ", ".join(sorted(forbidden))})
        return super().write(vals)
