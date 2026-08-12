# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Normalized event code master.

The track-trace pipeline ingests events from many sources: internal
state transitions, carrier webhooks (one per carrier API), spreadsheet
imports for backfill. Each source uses its own vocabulary. The code
master collapses that vocabulary into a small set of customer-facing
codes so the timeline is readable and so subscriptions can target
events by category rather than by carrier-specific string.

The master is seeded by config data; operators may add codes for
domain extensions but the seeded codes are protected by an XML id
guard against rename and deletion.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


SEEDED_PREFIX = "eh_log_track_trace.event_code_"


class EhLogTrackEventCode(models.Model):
    _name = "eh.log.track.event.code"
    _description = "Tracking Event Code"
    _order = "sequence, code"

    code = fields.Char(
        string="Code",
        required=True,
        help=(
            "Stable, machine-readable identifier. Subscriptions and "
            "carrier mappings reference this value, never the label."
        ),
    )
    name = fields.Char(
        string="Label",
        required=True,
        translate=True,
        help="Customer-facing label rendered on the public timeline.",
    )
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [
            ("origin", "Origin"),
            ("transit", "Transit"),
            ("destination", "Destination"),
            ("exception", "Exception"),
            ("delivery", "Delivery"),
        ],
        string="Category",
        required=True,
        default="transit",
        help=(
            "Coarse grouping used to colour-code the timeline and to "
            "let subscriptions opt into a whole class of events."
        ),
    )
    is_milestone = fields.Boolean(
        string="Milestone",
        default=False,
        help=(
            "If set, raising this event triggers notifications on all "
            "matching subscriptions. Non-milestone events still appear "
            "on the timeline but do not page customers."
        ),
    )
    default_description = fields.Char(
        string="Default Description",
        translate=True,
        help=(
            "Used as the timeline description when the event source "
            "does not supply a per-event description."
        ),
    )
    icon_name = fields.Char(
        string="Icon Name",
        default="fa-circle-info",
        help=(
            "Symbol-name only (no path or colour). The public template "
            "maps the name to the SVG sprite asset; this keeps the "
            "code master decoupled from the renderer."
        ),
    )
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        'unique(code)',
        'Tracking event code must be unique.',
    )

    def _is_seeded(self):
        self.ensure_one()
        ref = self.env["ir.model.data"].search([
            ("model", "=", self._name),
            ("res_id", "=", self.id),
            ("module", "=", "eh_log_track_trace"),
        ], limit=1)
        return bool(ref)

    def write(self, vals):
        if "code" in vals:
            for record in self:
                if record._is_seeded() and vals["code"] != record.code:
                    raise UserError(_(
                        "[EHL-TRK-002] Seeded tracking event code "
                        "%(code)s cannot be renamed; create a new "
                        "code instead."
                    ) % {"code": record.code})
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record._is_seeded():
                raise UserError(_(
                    "[EHL-TRK-003] Seeded tracking event code "
                    "%(code)s cannot be deleted; archive it instead."
                ) % {"code": record.code})
        return super().unlink()
