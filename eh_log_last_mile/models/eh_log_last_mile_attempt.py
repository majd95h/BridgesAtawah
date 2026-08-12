# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Per-attempt log entry. Append-only at the API layer."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


ATTEMPT_OUTCOMES = [
    ("delivered", "Delivered"),
    ("customer_not_home", "Customer Not Home"),
    ("refused", "Refused"),
    ("address_incorrect", "Address Incorrect"),
    ("damaged", "Damaged in Transit"),
    ("vehicle_breakdown", "Vehicle Breakdown"),
    ("other", "Other"),
]


class EhLogLastMileAttempt(models.Model):
    _name = "eh.log.last.mile.attempt"
    _description = "Last Mile Attempt"
    _order = "delivery_id, happened_at desc, id desc"
    _rec_name = "happened_at"

    delivery_id = fields.Many2one(
        "eh.log.last.mile.delivery",
        string="Delivery",
        required=True,
        ondelete="cascade",
        index=True,
    )

    happened_at = fields.Datetime(
        string="Happened At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )

    outcome = fields.Selection(
        selection=ATTEMPT_OUTCOMES,
        string="Outcome",
        required=True,
        index=True,
    )

    notes = fields.Text(string="Notes")

    gps_latitude = fields.Float(
        string="GPS Latitude",
        digits=(9, 6),
    )

    gps_longitude = fields.Float(
        string="GPS Longitude",
        digits=(9, 6),
    )

    company_id = fields.Many2one(
        related="delivery_id.company_id",
        store=True,
        index=True,
    )

    def write(self, vals):
        if not self.env.context.get("eh_log_last_mile_attempt_internal_write"):
            forbidden = set(vals) - {"notes"}
            if forbidden:
                raise UserError(_(
                    "[EHL-LM-ATT-001] Attempt entries are append-only. "
                    "Only the notes field can be updated after capture; "
                    "the following are immutable: %(fields)s."
                ) % {"fields": ", ".join(sorted(forbidden))})
        return super().write(vals)
