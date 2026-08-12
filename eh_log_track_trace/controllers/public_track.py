# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Public tracking page controller.

A single un-authenticated route renders the customer timeline. All
the work happens in the trackable mixin's resolve_token; the
controller exists only to bind a URL to a QWeb template and to fall
back to a "not found" page if the token does not match.

The controller stays deliberately thin: no business logic, no
side-effects on the database. A bot scraping random tokens hits the
404 path and never enumerates a real record.
"""
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EhLogTrackPublicController(http.Controller):
    @http.route(
        ["/track/<string:token>"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
        csrf=False,
    )
    def track(self, token, **kwargs):
        Trackable = request.env["eh.log.track.trackable"].sudo()
        record = Trackable.resolve_token(token)
        if not record:
            return request.render(
                "eh_log_track_trace.public_track_not_found",
                {"token": token},
                headers={"Cache-Control": "no-store"},
            )
        Event = request.env["eh.log.track.event"].sudo()
        events = Event.search([
            ("res_model", "=", record._name),
            ("res_id", "=", record.id),
        ], order="occurred_at asc, id asc")
        timeline = [event.to_public_dict() for event in events]
        # The reference shown on the public page should be the
        # carrier-facing reference if present, otherwise the record
        # name. Never expose internal IDs.
        public_reference = (
            record.tracking_reference
            if "tracking_reference" in record._fields
            and record.tracking_reference
            else record.display_name
        )
        return request.render(
            "eh_log_track_trace.public_track_page",
            {
                "reference": public_reference,
                "timeline": timeline,
                "model_label": record._description,
            },
            headers={"Cache-Control": "no-store"},
        )
