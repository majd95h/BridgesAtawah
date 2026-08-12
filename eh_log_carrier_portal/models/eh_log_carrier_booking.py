# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Carrier booking lifecycle.

A booking is a chosen quote turned into an instruction the carrier
acts on. State machine:

    requested -> accepted -> confirmed -> closed
                          \-> cancelled

The accepted state means the carrier has acknowledged receipt; the
confirmed state means the carrier has issued an internal reference
and committed capacity. Polling cron walks the accepted state for
status updates.

Direct writes to state are blocked. The cancellation window is a
configurable cutoff (in hours after confirmation) past which the
cancel action raises rather than silently failing.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "requested": ("accepted", "cancelled"),
    "accepted": ("confirmed", "cancelled"),
    "confirmed": ("closed", "cancelled"),
    "closed": (),
    "cancelled": (),
}

# Default cancellation window in hours. Operators can override per
# carrier through a future contract_terms structure; for now the
# default ships in code so a fresh install behaves predictably.
DEFAULT_CANCEL_WINDOW_HOURS = 24


class EhLogCarrierBooking(models.Model):
    _name = "eh.log.carrier.booking"
    _description = "Carrier Booking"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name", "carrier_booking_reference"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("requested", "Requested"),
            ("accepted", "Accepted"),
            ("confirmed", "Confirmed"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="requested",
        tracking=True,
        copy=False,
    )
    quote_id = fields.Many2one(
        "eh.log.carrier.rate.quote",
        string="Source Quote",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    request_id = fields.Many2one(
        related="quote_id.request_id",
        store=True,
        readonly=True,
    )
    carrier_profile_id = fields.Many2one(
        related="quote_id.carrier_profile_id",
        store=True,
        readonly=True,
    )
    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
        ondelete="set null",
        tracking=True,
    )
    carrier_booking_reference = fields.Char(
        string="Carrier Booking Reference",
        tracking=True,
        copy=False,
    )
    accepted_at = fields.Datetime(
        string="Accepted At",
        readonly=True,
        copy=False,
    )
    confirmed_at = fields.Datetime(
        string="Confirmed At",
        readonly=True,
        copy=False,
    )
    cancelled_at = fields.Datetime(
        string="Cancelled At",
        readonly=True,
        copy=False,
    )
    cancellation_reason = fields.Char(string="Cancellation Reason")
    last_status_polled_at = fields.Datetime(
        string="Last Status Polled",
        readonly=True,
    )
    last_status_message = fields.Char(string="Last Status Message")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.carrier.booking"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for booking in self:
            current = booking.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Booking %(name)s cannot move from %(from)s to "
                      "%(to)s.") % {
                        "name": booking.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            booking.with_context(
                eh_log_carrier_internal_state_write=True
            ).write({"state": target_state})

    def action_request(self):
        """Send the book message to the carrier."""
        for booking in self:
            adapter = booking.carrier_profile_id.get_adapter()
            payload = booking._build_book_payload()
            result = adapter.call(
                "book", payload, related_model=self._name,
            )
            if not result.ok:
                raise UserError(_(
                    "[EHL-CAR-007] Carrier %(carrier)s rejected the "
                    "booking: %(error)s"
                ) % {
                    "carrier": booking.carrier_profile_id.code,
                    "error": result.error or _("unknown"),
                })
            parsed = result.parsed or {}
            booking.with_context(
                eh_log_carrier_internal_state_write=True,
            ).write({
                "state": "accepted",
                "carrier_booking_reference": parsed.get("booking_reference", ""),
                "accepted_at": fields.Datetime.now(),
            })

    def action_confirm(self):
        for booking in self:
            booking._transition_state("confirmed")
            booking.confirmed_at = fields.Datetime.now()

    def action_close(self):
        self._transition_state("closed")

    def action_cancel(self):
        for booking in self:
            booking._check_cancel_window()
            adapter = booking.carrier_profile_id.get_adapter()
            payload = {
                "booking_reference": booking.carrier_booking_reference or "",
            }
            result = adapter.call(
                "cancel", payload, related_model=self._name,
            )
            if not result.ok:
                raise UserError(_(
                    "[EHL-CAR-008] Carrier %(carrier)s could not "
                    "cancel: %(error)s"
                ) % {
                    "carrier": booking.carrier_profile_id.code,
                    "error": result.error or _("unknown"),
                })
            booking._transition_state("cancelled")
            booking.cancelled_at = fields.Datetime.now()

    def _check_cancel_window(self):
        self.ensure_one()
        if self.state != "confirmed":
            return
        if not self.confirmed_at:
            return
        cutoff = fields.Datetime.now() - fields.Datetime.now() + self.confirmed_at
        # Compute hours elapsed since confirmation in pure Python.
        delta = fields.Datetime.now() - self.confirmed_at
        hours_since = delta.total_seconds() / 3600.0
        if hours_since > DEFAULT_CANCEL_WINDOW_HOURS:
            raise UserError(_(
                "[EHL-CAR-009] Booking %(name)s confirmed "
                "%(hours).1f hours ago; the cancellation window of "
                "%(window)d hours has closed."
            ) % {
                "name": self.name,
                "hours": hours_since,
                "window": DEFAULT_CANCEL_WINDOW_HOURS,
            })

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_carrier_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-CAR-010] Booking state must change via the "
                "action buttons."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Adapter payloads
    # ------------------------------------------------------------------
    def _build_book_payload(self):
        self.ensure_one()
        request = self.request_id
        return {
            "booking_reference": self.name,
            "quote_reference": self.quote_id.carrier_quote_reference or "",
            "service_name": self.quote_id.service_name or "",
            "freight_job_reference": (
                self.freight_job_id.name if self.freight_job_id else ""
            ),
            "origin": {
                "country_code": request.origin_country_id.code,
                "location_code": request.origin_location_code or "",
            },
            "destination": {
                "country_code": request.destination_country_id.code,
                "location_code": request.destination_location_code or "",
            },
            "ready_by": request.ready_by_date.isoformat(),
            "cargo": {
                "weight_kg": request.weight_kg,
                "volume_cbm": request.volume_cbm,
                "packages": request.package_count,
                "dangerous_goods": request.is_dangerous_goods,
            },
        }

    # ------------------------------------------------------------------
    # Status polling cron
    # ------------------------------------------------------------------
    @api.model
    def cron_poll_status(self):
        """Refresh status for all accepted/confirmed bookings."""
        candidates = self.search([
            ("state", "in", ("accepted", "confirmed")),
            ("carrier_profile_id.can_track", "=", True),
        ])
        polled = 0
        for booking in candidates:
            try:
                adapter = booking.carrier_profile_id.get_adapter()
                payload = {
                    "booking_reference": booking.carrier_booking_reference or "",
                }
                result = adapter.call(
                    "track_status", payload, related_model=self._name,
                )
            except Exception as exc:
                _logger.exception(
                    "Booking %s status poll failed: %s",
                    booking.name, exc,
                )
                continue
            if not result.ok:
                continue
            parsed = result.parsed or {}
            booking.last_status_polled_at = fields.Datetime.now()
            booking.last_status_message = parsed.get("status_message", "")
            polled += 1
        _logger.info(
            "Carrier booking status poll: %d booking(s) refreshed", polled,
        )
        return polled
