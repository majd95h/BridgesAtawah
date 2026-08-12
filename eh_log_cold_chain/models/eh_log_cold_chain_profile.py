# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Cold chain profile master.

A reusable temperature regime with thresholds and alert behaviour.
Operators pick a profile per quotation; the monitoring run inherits
the thresholds and alerts when readings cross them.
"""
from odoo import _, api, fields, models

from odoo.addons.eh_log_base.exceptions import EhLogValidationError


class EhLogColdChainProfile(models.Model):
    _name = "eh.log.cold.chain.profile"
    _description = "Cold Chain Profile"
    _order = "category, name"
    _rec_names_search = ["code", "name"]

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
        help="Stable identifier (PHARMA-2-8, FROZEN-18, AMB-15-25, ...).",
    )

    name = fields.Char(string="Name", required=True, translate=True)

    category = fields.Selection(
        selection=[
            ("pharma", "Pharma (2 to 8 degC)"),
            ("controlled_room", "Controlled Room (15 to 25 degC)"),
            ("chilled", "Chilled (-2 to 8 degC)"),
            ("frozen", "Frozen (-18 degC and below)"),
            ("deep_frozen", "Deep Frozen (-45 degC and below)"),
            ("dry_ice", "Dry Ice"),
            ("custom", "Custom"),
        ],
        string="Category",
        required=True,
        index=True,
    )

    temperature_min = fields.Float(
        string="Min Temperature (degC)",
        required=True,
        help="Lower threshold. Readings below this trigger a deviation "
             "after the alert window elapses.",
    )

    temperature_max = fields.Float(
        string="Max Temperature (degC)",
        required=True,
        help="Upper threshold. Readings above this trigger a deviation "
             "after the alert window elapses.",
    )

    humidity_min = fields.Float(string="Min Humidity (%)", default=0.0)
    humidity_max = fields.Float(string="Max Humidity (%)", default=100.0)
    monitor_humidity = fields.Boolean(
        string="Monitor Humidity",
        default=False,
        help="When True, readings must include humidity and the "
             "thresholds above are enforced.",
    )

    sampling_cadence_minutes = fields.Integer(
        string="Sampling Cadence (minutes)",
        default=15,
        help="Expected interval between readings. Used by the gap "
             "detector to flag missing data.",
    )

    alert_window_minutes = fields.Integer(
        string="Alert Window (minutes)",
        default=30,
        help="Minimum continuous duration that a threshold must be "
             "breached before a deviation is raised. Buffers transient "
             "spikes (e.g. door open during gate-in).",
    )

    excursion_grace_minutes = fields.Integer(
        string="Excursion Grace (minutes)",
        default=15,
        help="Time after a deviation closes before the run returns "
             "to nominal status. Allows readings to fully stabilise.",
    )

    description = fields.Text(translate=True)

    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'Profile code must be unique.',
    )

    @api.constrains("temperature_min", "temperature_max")
    def _check_temperature_range(self):
        for record in self:
            if record.temperature_min >= record.temperature_max:
                raise EhLogValidationError(
                    120,
                    _(
                        "Profile %(name)s has min temperature "
                        "%(min).2f >= max %(max).2f. The min must be "
                        "strictly less than the max."
                    ) % {
                        "name": record.name,
                        "min": record.temperature_min,
                        "max": record.temperature_max,
                    },
                )

    @api.constrains("monitor_humidity", "humidity_min", "humidity_max")
    def _check_humidity_range(self):
        for record in self:
            if not record.monitor_humidity:
                continue
            if record.humidity_min >= record.humidity_max:
                raise EhLogValidationError(
                    121,
                    _(
                        "Profile %(name)s has humidity min "
                        "%(min).1f%% >= max %(max).1f%% but humidity "
                        "monitoring is enabled."
                    ) % {
                        "name": record.name,
                        "min": record.humidity_min,
                        "max": record.humidity_max,
                    },
                )

    @api.depends("code", "name", "temperature_min", "temperature_max")
    def _compute_display_name(self):
        for record in self:
            range_str = f"{record.temperature_min:g} to {record.temperature_max:g}degC"
            record.display_name = (
                f"[{record.code}] {record.name} ({range_str})"
                if record.code else f"{record.name} ({range_str})"
            )
