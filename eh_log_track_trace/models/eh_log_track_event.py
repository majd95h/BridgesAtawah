# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Append-only normalized event log.

Every customer-visible state change in the suite lands here, regardless
of the originating record type. The log is the single source of truth
for the public tracking page and for milestone notifications.

Append-only means: create is open to internal users via the
log_track_event helper on the trackable mixin; direct writes to
operational fields are blocked after creation. The notes field is
mutable so an operator can annotate an event after the fact (e.g.,
"customs hold cleared by broker at 14:00").
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Fields locked once the event row exists. Mirrors the pattern used by
# the last-mile attempt log: outcome and timestamp are immutable, the
# free-text notes column is not.
LOCKED_FIELDS = (
    "res_model",
    "res_id",
    "event_code_id",
    "occurred_at",
    "source",
    "raw_payload",
    "company_id",
)


class EhLogTrackEvent(models.Model):
    _name = "eh.log.track.event"
    _description = "Tracking Event"
    _order = "occurred_at desc, id desc"
    _rec_name = "display_name"

    res_model = fields.Char(
        string="Source Model",
        required=True,
        index=True,
        help=(
            "Technical name of the trackable model the event belongs "
            "to. Combined with res_id this points back to the source "
            "record without needing a foreign key per model."
        ),
    )
    res_id = fields.Integer(
        string="Source ID",
        required=True,
        index=True,
    )
    event_code_id = fields.Many2one(
        "eh.log.track.event.code",
        string="Event Code",
        required=True,
        ondelete="restrict",
        index=True,
    )
    code = fields.Char(
        related="event_code_id.code",
        store=True,
        index=True,
    )
    category = fields.Selection(
        related="event_code_id.category",
        store=True,
    )
    is_milestone = fields.Boolean(
        related="event_code_id.is_milestone",
        store=True,
    )
    description = fields.Char(
        string="Description",
        help=(
            "One-line description rendered on the public timeline. "
            "Falls back to the event code default if the source "
            "passes nothing."
        ),
    )
    location = fields.Char(
        string="Location",
        help=(
            "Free-text location string from the source. The public "
            "page renders it under the event description."
        ),
    )
    occurred_at = fields.Datetime(
        string="Occurred At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    source = fields.Selection(
        [
            ("internal", "Internal"),
            ("webhook", "Carrier Webhook"),
            ("import", "Import"),
            ("api", "API"),
        ],
        string="Source",
        default="internal",
        required=True,
        help=(
            "Where the event originated. The raw inbound body of a "
            "webhook event is kept on the raw_payload field."
        ),
    )
    raw_payload = fields.Text(
        string="Raw Payload",
        help=(
            "The unmodified payload (JSON, XML, etc.) from the "
            "carrier webhook. Internal-source events leave this "
            "blank. Used for forensics when a customer disputes a "
            "timeline entry."
        ),
    )
    notes = fields.Text(
        string="Operator Notes",
        help=(
            "Mutable free-text annotation. Distinct from the event "
            "description: the description is shown publicly; notes "
            "are internal."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    display_name = fields.Char(
        compute="_compute_display_name",
        store=False,
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("event_code_id", "occurred_at")
    def _compute_display_name(self):
        for event in self:
            label = event.event_code_id.name or event.code or _("Event")
            ts = (
                fields.Datetime.to_string(event.occurred_at)
                if event.occurred_at else ""
            )
            event.display_name = f"{label} - {ts}".strip(" -")

    # ------------------------------------------------------------------
    # Append-only enforcement
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_track_internal_create"):
            raise UserError(_(
                "[EHL-TRK-004] Tracking events must be created through "
                "log_track_event() on the source record, not by direct "
                "ORM write."
            ))
        events = super().create(vals_list)
        if not self.env.context.get("eh_log_track_skip_notify"):
            events._notify_subscribers()
        return events

    def write(self, vals):
        locked = set(LOCKED_FIELDS) & set(vals.keys())
        if locked:
            raise UserError(_(
                "[EHL-TRK-005] Tracking event field(s) %(fields)s are "
                "immutable after creation. Add a new event instead."
            ) % {"fields": ", ".join(sorted(locked))})
        return super().write(vals)

    def unlink(self):
        if self:
            raise UserError(_(
                "[EHL-TRK-006] Tracking events are append-only and "
                "cannot be deleted; archive the source record "
                "instead."
            ))
        return super().unlink()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify_subscribers(self):
        Subscription = self.env["eh.log.track.subscription"].sudo()
        Mail = self.env["mail.template"].sudo()
        template = self.env.ref(
            "eh_log_track_trace.email_template_track_event_milestone",
            raise_if_not_found=False,
        )
        if not template:
            return
        for event in self:
            if not event.is_milestone:
                continue
            subs = Subscription.search([
                ("res_model", "=", event.res_model),
                ("res_id", "=", event.res_id),
                ("active", "=", True),
                "|",
                ("event_code_ids", "=", False),
                ("event_code_ids", "in", event.event_code_id.id),
            ])
            for sub in subs:
                if not sub.partner_id.email:
                    continue
                template.with_context(
                    eh_log_track_subscription_id=sub.id,
                ).send_mail(
                    event.id,
                    email_values={"email_to": sub.partner_id.email},
                    force_send=False,
                )

    # ------------------------------------------------------------------
    # Public-page helper
    # ------------------------------------------------------------------
    def to_public_dict(self):
        """Return the public-safe representation of the event.

        Strips the raw payload, the notes, the source label, and any
        carrier-specific identifiers. Only the customer-facing fields
        survive.
        """
        self.ensure_one()
        return {
            "code": self.code,
            "label": self.event_code_id.name,
            "category": self.category,
            "icon": self.event_code_id.icon_name,
            "description": self.description or "",
            "location": self.location or "",
            "occurred_at": (
                fields.Datetime.to_string(self.occurred_at)
                if self.occurred_at else ""
            ),
        }
