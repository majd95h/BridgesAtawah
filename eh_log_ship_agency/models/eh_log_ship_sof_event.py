# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Statement of Facts (SOF) event log.

The SOF is the timestamped chronology of operational events on a
port call: pilot on board, tugs fast, first line ashore, gangway
down, cargo operations commenced, weather suspension, customs
inspection, and so on. The log is append-only because the SOF is the
primary evidence in a laytime dispute and rewriting history would
destroy that evidence.

State transitions on the port call emit a SOF event automatically.
Manual events are created by the operator through the SOF view; the
description is free-text and the occurred_at is operator-stamped to
reflect the actual time of the event rather than the time of data
entry (vessels often work overnight, with the agent updating the log
the next morning).
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Locked once the row exists. The notes column stays mutable so an
# operator can annotate a historic event after the fact (e.g.,
# "weather suspension actually 14:32, not 14:30").
LOCKED_FIELDS = (
    "port_call_id",
    "description",
    "occurred_at",
    "event_category",
    "company_id",
)


SOF_CATEGORIES = [
    ("operational", "Operational"),
    ("delay", "Delay"),
    ("weather", "Weather"),
    ("customs", "Customs"),
    ("safety", "Safety"),
    ("other", "Other"),
]


class EhLogShipSofEvent(models.Model):
    _name = "eh.log.ship.sof.event"
    _description = "Statement of Facts Event"
    _order = "occurred_at, id"

    port_call_id = fields.Many2one(
        "eh.log.ship.port.call",
        string="Port Call",
        required=True,
        ondelete="cascade",
        index=True,
    )
    description = fields.Char(
        string="Description",
        required=True,
        help="One-line operational event as it would appear on the SOF PDF.",
    )
    occurred_at = fields.Datetime(
        string="Occurred At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    event_category = fields.Selection(
        SOF_CATEGORIES,
        string="Category",
        default="operational",
    )
    counts_against_laytime = fields.Boolean(
        string="Against Laytime",
        default=True,
        help=(
            "If unticked, this event period is excluded from laytime "
            "consumption. Used for weather suspensions and other "
            "agreed exceptions."
        ),
    )
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_ship_internal_sof_create"):
            # Manual creates are also allowed but go through this
            # gate so the test can prove that direct ORM creation
            # by a script is the only path. The gate accepts manual
            # creates; this is intentional, the safeguard is against
            # accidental sync from external systems with no human
            # in the loop.
            pass
        return super().create(vals_list)

    def write(self, vals):
        locked = set(LOCKED_FIELDS) & set(vals.keys())
        if locked:
            raise UserError(_(
                "[EHL-SHP-010] SOF event field(s) %(fields)s are "
                "immutable after creation. Append a corrective "
                "event instead."
            ) % {"fields": ", ".join(sorted(locked))})
        return super().write(vals)

    def unlink(self):
        if self:
            raise UserError(_(
                "[EHL-SHP-011] SOF events are append-only and "
                "cannot be deleted."
            ))
        return super().unlink()
