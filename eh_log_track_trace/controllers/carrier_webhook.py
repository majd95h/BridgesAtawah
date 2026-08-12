# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Inbound carrier webhook controller.

Endpoints follow the pattern ``/track/event/<carrier_name>``. The
controller enforces a strict ordering: signature first, parse second,
persist last. Any failure short-circuits with a clean HTTP status
code; the response body is always JSON so the carrier's retry logic
can read the error.

A successful call ingests one event. Carriers that batch multiple
events per call are not supported here by design: keeping the
contract one-event-per-request makes each call atomic at the database
level and lets the retry semantics stay obvious.
"""
import hashlib
import hmac
import json
import logging

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

# HTTP status codes used in the JSON responses. Bound to constants so
# the test suite can assert against the labels and the no-hardcoding
# checker is satisfied that the integers are protocol-spec values.
HTTP_OK = 200  # noqa: gcclog-hardcode RFC 9110 status code
HTTP_BAD_REQUEST = 400  # noqa: gcclog-hardcode RFC 9110 status code
HTTP_UNAUTHORIZED = 401  # noqa: gcclog-hardcode RFC 9110 status code
HTTP_NOT_FOUND = 404  # noqa: gcclog-hardcode RFC 9110 status code
HTTP_UNPROCESSABLE = 422  # noqa: gcclog-hardcode RFC 9110 status code


def _json_response(payload, status):
    return request.make_response(
        json.dumps(payload),
        headers=[("Content-Type", "application/json")],
        status=status,
    )


class EhLogTrackWebhookController(http.Controller):
    @http.route(
        ["/track/event/<string:carrier_name>"],
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def receive(self, carrier_name, **kwargs):
        Endpoint = request.env["eh.log.track.webhook.endpoint"].sudo()
        endpoint = Endpoint.search([
            ("carrier_name", "=", carrier_name),
            ("active", "=", True),
        ], limit=1)
        if not endpoint:
            return _json_response(
                {"error": _("unknown carrier"), "code": "EHL-TRK-101"},
                HTTP_NOT_FOUND,
            )

        body = request.httprequest.get_data()
        signature = request.httprequest.headers.get(endpoint.signature_header)
        if not signature:
            return _json_response(
                {"error": _("missing signature"), "code": "EHL-TRK-102"},
                HTTP_UNAUTHORIZED,
            )

        try:
            secret = endpoint.fetch_secret()
        except Exception:
            _logger.exception(
                "Could not resolve credentials for carrier %s",
                carrier_name,
            )
            return _json_response(
                {"error": _("misconfigured"), "code": "EHL-TRK-103"},
                HTTP_UNAUTHORIZED,
            )

        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            _logger.warning(
                "Webhook signature mismatch for carrier %s",
                carrier_name,
            )
            return _json_response(
                {"error": _("bad signature"), "code": "EHL-TRK-104"},
                HTTP_UNAUTHORIZED,
            )

        try:
            payload = json.loads(body)
        except ValueError:
            return _json_response(
                {"error": _("malformed JSON"), "code": "EHL-TRK-105"},
                HTTP_BAD_REQUEST,
            )

        reference = endpoint.extract(payload, endpoint.reference_path)
        carrier_code = endpoint.extract(payload, endpoint.event_code_path)
        if not reference or not carrier_code:
            return _json_response(
                {
                    "error": _("missing required field"),
                    "code": "EHL-TRK-106",
                },
                HTTP_UNPROCESSABLE,
            )

        record = endpoint.resolve_record(reference)
        if not record:
            return _json_response(
                {"error": _("unknown reference"), "code": "EHL-TRK-107"},
                HTTP_NOT_FOUND,
            )

        event_code = endpoint.map_carrier_code(carrier_code)
        if not event_code:
            _logger.info(
                "Unmapped carrier event code %s for %s; ignored.",
                carrier_code, carrier_name,
            )
            return _json_response(
                {"status": _("ignored")},
                HTTP_OK,
            )

        location = endpoint.extract(payload, endpoint.location_path) or ""
        occurred_at = endpoint.extract(payload, endpoint.occurred_at_path)
        record.log_track_event(
            event_code.code,
            description=None,
            location=location,
            occurred_at=occurred_at or None,
            source="webhook",
            raw_payload=body.decode("utf-8", errors="replace"),
        )
        return _json_response(
            {"status": _("accepted")},
            HTTP_OK,
        )
