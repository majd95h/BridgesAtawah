# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Inbound carrier webhook endpoint configuration.

A row per carrier integration. The webhook controller looks up the
endpoint by the path identifier in the inbound URL, fetches the
shared secret through the credentials helper, validates the HMAC
signature on the inbound request, then delegates to the endpoint's
mapping table to translate the carrier event code into a normalized
eh.log.track.event.code.

The endpoint also stores the carrier's reference-key configuration:
which JSON path on the inbound payload identifies the source record,
and how to resolve that identifier back to a trackable record. This
keeps the controller free of carrier-specific logic.
"""
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


# Default JSON pointers used by most carriers; overridden per-endpoint
# when a vendor uses a non-conventional schema. Stored as strings, not
# constants in code, so an operator can adjust without a deploy.
DEFAULT_REFERENCE_PATH = "shipment_reference"
DEFAULT_EVENT_CODE_PATH = "event_code"
DEFAULT_OCCURRED_AT_PATH = "occurred_at"
DEFAULT_LOCATION_PATH = "location"


class EhLogTrackWebhookEndpoint(models.Model):
    _name = "eh.log.track.webhook.endpoint"
    _description = "Carrier Webhook Endpoint"
    _order = "carrier_name"

    name = fields.Char(
        string="Name",
        required=True,
        help="Operator-facing name used in logs and the audit trail.",
    )
    carrier_name = fields.Char(
        string="Carrier",
        required=True,
        index=True,
        help=(
            "Lower-case carrier identifier appearing in the inbound "
            "URL: /track/event/<carrier_name>. No spaces."
        ),
    )
    secret_key = fields.Char(
        string="Credentials Key",
        required=True,
        help=(
            "Lookup key passed to the credentials helper to fetch the "
            "shared secret. Resolves through env var, encrypted "
            "ir.config_parameter, then default."
        ),
    )
    signature_header = fields.Char(
        string="Signature Header",
        default="X-Eh-Track-Signature",
        required=True,
        help=(
            "HTTP header carrying the HMAC-SHA256 hex digest the "
            "carrier signs the request body with."
        ),
    )
    reference_path = fields.Char(
        string="Reference JSON Path",
        default=DEFAULT_REFERENCE_PATH,
        required=True,
        help=(
            "Dotted JSON path to the carrier's shipment reference. "
            "The reference matches against the source record's "
            "tracking_reference field."
        ),
    )
    event_code_path = fields.Char(
        string="Event Code JSON Path",
        default=DEFAULT_EVENT_CODE_PATH,
        required=True,
    )
    occurred_at_path = fields.Char(
        string="Occurred-At JSON Path",
        default=DEFAULT_OCCURRED_AT_PATH,
        required=True,
    )
    location_path = fields.Char(
        string="Location JSON Path",
        default=DEFAULT_LOCATION_PATH,
        help="Optional. Leave blank if the carrier omits location.",
    )
    target_model = fields.Selection(
        selection="_selection_target_model",
        string="Target Model",
        required=True,
        default="eh.log.freight.job",
        help=(
            "Which trackable model the webhook posts events against. "
            "Most carrier integrations target freight jobs; last-mile "
            "carriers target deliveries."
        ),
    )
    mapping_ids = fields.One2many(
        "eh.log.track.webhook.mapping",
        "endpoint_id",
        string="Code Mapping",
        help=(
            "One row per carrier-supplied event code, mapping it to a "
            "normalized eh.log.track.event.code. Inbound events with "
            "no mapping are ignored after a warning is logged."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _carrier_name_unique = models.Constraint(
        'unique(carrier_name, company_id)',
        'Carrier name must be unique per company.',
    )

    @api.model
    def _selection_target_model(self):
        Trackable = self.env["eh.log.track.trackable"]
        models_list = Trackable._inheriting_models()
        return [
            (m, self.env[m]._description or m)
            for m in models_list
        ]

    @api.constrains("carrier_name")
    def _check_carrier_name(self):
        for endpoint in self:
            if not endpoint.carrier_name:
                continue
            if not endpoint.carrier_name.replace("_", "").isalnum():
                raise ValidationError(_(
                    "[EHL-TRK-009] Carrier name %(name)s must be "
                    "alphanumeric or underscore only."
                ) % {"name": endpoint.carrier_name})
            if endpoint.carrier_name.lower() != endpoint.carrier_name:
                raise ValidationError(_(
                    "[EHL-TRK-010] Carrier name %(name)s must be "
                    "lower-case."
                ) % {"name": endpoint.carrier_name})

    # ------------------------------------------------------------------
    # Webhook ingestion
    # ------------------------------------------------------------------
    def fetch_secret(self):
        self.ensure_one()
        Credentials = self.env["eh.log.credentials"]
        return Credentials.get(
            purpose=f"webhook_{self.carrier_name}",
            param_key=self.secret_key,
            company_id=self.company_id.id,
        )

    def map_carrier_code(self, carrier_code):
        self.ensure_one()
        for row in self.mapping_ids:
            if row.carrier_code == carrier_code:
                return row.event_code_id
        return self.env["eh.log.track.event.code"]

    def resolve_record(self, reference):
        """Look up a trackable record from the inbound carrier ref."""
        self.ensure_one()
        if not reference:
            return self.env[self.target_model].browse()
        Model = self.env[self.target_model].sudo()
        # Convention: trackable models expose a tracking_reference
        # field if they accept inbound matches by external reference.
        # If the field is absent, fall back to the record name. This
        # keeps the integration usable even for models that have not
        # yet added a dedicated reference field.
        if "tracking_reference" in Model._fields:
            return Model.search([("tracking_reference", "=", reference)], limit=1)
        return Model.search([("name", "=", reference)], limit=1)

    def extract(self, payload, path):
        """Walk a dotted JSON path through the payload."""
        self.ensure_one()
        if not path:
            return None
        current = payload
        for segment in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
            if current is None:
                return None
        return current


class EhLogTrackWebhookMapping(models.Model):
    _name = "eh.log.track.webhook.mapping"
    _description = "Carrier Event Code Mapping"
    _order = "endpoint_id, carrier_code"

    endpoint_id = fields.Many2one(
        "eh.log.track.webhook.endpoint",
        string="Endpoint",
        required=True,
        ondelete="cascade",
    )
    carrier_code = fields.Char(
        string="Carrier Event Code",
        required=True,
        help="Verbatim event code as the carrier emits it.",
    )
    event_code_id = fields.Many2one(
        "eh.log.track.event.code",
        string="Normalized Event",
        required=True,
        ondelete="restrict",
    )

    _carrier_code_unique = models.Constraint(
        'unique(endpoint_id, carrier_code)',
        'A carrier event code may only map once per endpoint.',
    )
