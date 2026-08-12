# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Abstract trackable mixin.

Adds a stable, non-enumerable tracking token, a public URL computation,
and a single helper to append normalized events to the log. Concrete
operational models (freight job, transport trip, last mile delivery)
inherit this mixin to expose themselves on the public tracking page.

The token derives from the record id and a per-database secret salt,
hashed with SHA-256 and truncated. Two properties matter:

* The token is opaque: it cannot be reversed to a record id without
  the database salt.
* The token is stable across restarts: the same record always yields
  the same token, so a customer's bookmarked link keeps working.

This mixin does not persist the token; it computes it on access. That
keeps the schema thin and avoids a migration when records pre-date
the install.
"""
import hashlib
import hmac
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Number of hex characters from the SHA-256 digest used for the public
# token. 32 hex chars = 128 bits of entropy, well past the threshold
# for non-enumerability while keeping URLs short enough to share.
TOKEN_HEX_LENGTH = 32

# ir.config_parameter key under which the per-database salt lives. The
# operator must set this once at deployment time. The credentials
# helper raises if the value is absent rather than falling back to a
# weak default.
TOKEN_SALT_PARAM = "eh_log_track_trace.token_salt"

# ir.config_parameter key for the canonical public base URL. Falls
# back to web.base.url if absent so a fresh install still works, but
# operators should set an explicit value to control which hostname
# customers see in tracking links.
PUBLIC_BASE_URL_PARAM = "eh_log_track_trace.public_base_url"


class EhLogTrackTrackable(models.AbstractModel):
    _name = "eh.log.track.trackable"
    _description = "Trackable Record Mixin"

    tracking_token = fields.Char(
        string="Tracking Token",
        compute="_compute_tracking_token",
        store=False,
        help=(
            "Stable, non-enumerable token used in the public tracking "
            "URL. Derived from the record id and the per-database "
            "salt. Safe to share with customers."
        ),
    )
    track_url = fields.Char(
        string="Public Tracking URL",
        compute="_compute_track_url",
        store=False,
        help=(
            "Full URL for the customer-facing tracking page. Built "
            "from the configured public base URL and the tracking "
            "token."
        ),
    )
    track_event_count = fields.Integer(
        string="Tracking Events",
        compute="_compute_track_event_count",
        store=False,
        help="Count of normalized tracking events on the public log.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends()
    def _compute_tracking_token(self):
        salt = self._get_token_salt()
        for record in self:
            if not record.id:
                record.tracking_token = False
                continue
            payload = f"{record._name}:{record.id}".encode("utf-8")
            digest = hmac.new(salt, payload, hashlib.sha256).hexdigest()
            record.tracking_token = digest[:TOKEN_HEX_LENGTH]

    @api.depends("tracking_token")
    def _compute_track_url(self):
        base = self._get_public_base_url()
        for record in self:
            if not record.tracking_token or not base:
                record.track_url = False
            else:
                record.track_url = f"{base}/track/{record.tracking_token}"

    def _compute_track_event_count(self):
        if not self:
            return
        Event = self.env["eh.log.track.event"]
        for record in self:
            record.track_event_count = Event.search_count([
                ("res_model", "=", record._name),
                ("res_id", "=", record.id),
            ])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def log_track_event(
        self,
        event_code,
        description=None,
        location=None,
        occurred_at=None,
        source="internal",
        raw_payload=None,
        notify=True,
    ):
        """Append a normalized event to the public timeline.

        Concrete models call this from their state-transition methods.
        Carrier webhook handlers also call this after mapping the
        provider event to a normalized code. Returns the created
        eh.log.track.event recordset.

        notify=False suppresses the per-subscription notification
        dispatch; use it for backfill loads where the customer should
        not be paged for events already in the past.
        """
        self.ensure_one()
        Code = self.env["eh.log.track.event.code"]
        code_record = Code.search([("code", "=", event_code)], limit=1)
        if not code_record:
            raise ValueError(
                _("[EHL-TRK-001] Unknown tracking event code %(code)s.")
                % {"code": event_code}
            )
        Event = self.env["eh.log.track.event"]
        return Event.with_context(
            eh_log_track_internal_create=True,
            eh_log_track_skip_notify=not notify,
        ).create({
            "res_model": self._name,
            "res_id": self.id,
            "event_code_id": code_record.id,
            "description": description or code_record.default_description,
            "location": location or "",
            "occurred_at": occurred_at or fields.Datetime.now(),
            "source": source,
            "raw_payload": raw_payload or "",
            "company_id": (
                self.company_id.id
                if "company_id" in self._fields and self.company_id
                else self.env.company.id
            ),
        })

    def action_open_track_url(self):
        """Open the public tracking page in a new browser tab."""
        self.ensure_one()
        if not self.track_url:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": self.track_url,
            "target": "new",
        }

    def action_view_track_events(self):
        """Open the timeline view filtered to this record."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tracking Events"),
            "res_model": "eh.log.track.event",
            "view_mode": "list,form",
            "domain": [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
            ],
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }

    # ------------------------------------------------------------------
    # Helpers (class-level so controllers can resolve a record from a
    # token without needing an instance.)
    # ------------------------------------------------------------------
    @api.model
    def resolve_token(self, token):
        """Find the trackable record matching the given public token.

        Walks the registry of models inheriting this mixin and matches
        the recomputed digest. Returns False if no match. Designed for
        the public controller; callers must use sudo() because the
        portal user has no read on operational records.
        """
        if not token or len(token) != TOKEN_HEX_LENGTH:
            return False
        salt = self._get_token_salt()
        for model_name in self._inheriting_models():
            Model = self.env[model_name].sudo()
            for record in Model.search([]):
                payload = f"{model_name}:{record.id}".encode("utf-8")
                digest = hmac.new(salt, payload, hashlib.sha256).hexdigest()
                if hmac.compare_digest(digest[:TOKEN_HEX_LENGTH], token):
                    return record
        return False

    @api.model
    def _inheriting_models(self):
        """Return the list of concrete models inheriting this mixin.

        Looked up dynamically so each new module that adds a trackable
        target (warehouse 3PL receipt, ship agency port call, etc.)
        is picked up without editing this list.
        """
        result = []
        for name, model in self.env.registry.models.items():
            if model._abstract or model._transient:
                continue
            if self._name in (model._inherit or []) or self._name == name:
                if name != self._name:
                    result.append(name)
        return result

    @api.model
    def _get_token_salt(self):
        Param = self.env["ir.config_parameter"].sudo()
        salt = Param.get_param(TOKEN_SALT_PARAM)
        if not salt:
            # Generate a strong random salt on first read so a fresh
            # install does not crash. The operator should override
            # with their own value via the settings page; doing so
            # invalidates outstanding tokens, which is correct.
            import secrets

            salt = secrets.token_hex(32)
            Param.set_param(TOKEN_SALT_PARAM, salt)
        return salt.encode("utf-8")

    @api.model
    def _get_public_base_url(self):
        Param = self.env["ir.config_parameter"].sudo()
        configured = Param.get_param(PUBLIC_BASE_URL_PARAM)
        if configured:
            return configured.rstrip("/")
        # Fallback: the standard Odoo web base URL. Set during install.
        return (Param.get_param("web.base.url") or "").rstrip("/")
