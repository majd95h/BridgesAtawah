# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Outbound EDI message queue.

State machine:

    draft -> queued -> sent -> acked -> closed
                         \-> rejected
                         \-> dead_letter

The dispatch cron walks queued rows, resolves the translator, builds
the payload, sends it through the partner's transport, and advances
the state. A failure increments retry_count; when retry_count exceeds
max_retries the row moves to dead_letter where an operator can
inspect and manually re-queue.

The payload is built once and stored. A dead-letter resume re-uses
the exact bytes the partner originally received (would have received,
in this case, since the original send did not succeed).
"""
import logging
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from ..translators import base as translator_base

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "draft": ("queued", "cancelled"),
    "queued": ("sent", "rejected", "dead_letter", "cancelled"),
    "sent": ("acked", "rejected", "closed"),
    "acked": ("closed",),
    "rejected": ("queued", "dead_letter", "cancelled"),
    "dead_letter": ("queued", "cancelled"),
    "closed": (),
    "cancelled": (),
}

DEFAULT_MAX_RETRIES = 5


class EhLogEdiOutbound(models.Model):
    _name = "eh.log.edi.outbound"
    _description = "EDI Outbound Message"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("acked", "Acknowledged"),
            ("rejected", "Rejected"),
            ("dead_letter", "Dead Letter"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    partner_config_id = fields.Many2one(
        "eh.log.edi.partner",
        string="Partner Configuration",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    partner_id = fields.Many2one(
        related="partner_config_id.partner_id",
        store=True,
        readonly=True,
    )
    message_type_id = fields.Many2one(
        "eh.log.edi.message.type",
        string="Message Type",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    source_model = fields.Char(
        string="Source Model",
        required=True,
        index=True,
    )
    source_id = fields.Integer(string="Source ID", required=True)
    payload = fields.Binary(
        string="Payload",
        attachment=True,
        readonly=True,
        help=(
            "Wire bytes built by the translator. Stored once and "
            "re-used on retry so the partner sees identical content "
            "across attempts."
        ),
    )
    payload_filename = fields.Char(string="Filename", readonly=True)
    transport_reference = fields.Char(
        string="Transport Reference",
        readonly=True,
        help=(
            "Identifier returned by the transport (SMTP message id, "
            "SFTP path, HTTP status). Useful for manual lookup."
        ),
    )
    sent_at = fields.Datetime(string="Sent At", readonly=True)
    acked_at = fields.Datetime(string="Acked At", readonly=True)
    retry_count = fields.Integer(string="Retries", default=0, readonly=True)
    max_retries = fields.Integer(
        string="Max Retries",
        default=DEFAULT_MAX_RETRIES,
        help=(
            "Cron retry budget. Reached: row moves to dead_letter; "
            "operator must manually re-queue or cancel."
        ),
    )
    error_message = fields.Text(string="Last Error")
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
                    "eh.log.edi.outbound"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for outbound in self:
            current = outbound.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Outbound message %(name)s cannot move from "
                      "%(from)s to %(to)s.") % {
                        "name": outbound.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            outbound.with_context(
                eh_log_edi_internal_state_write=True
            ).write({"state": target_state})

    def action_queue(self):
        for record in self:
            record._build_payload()
        self._transition_state("queued")

    def action_send(self):
        for record in self:
            if not record.payload:
                record._build_payload()
            try:
                result = record.partner_config_id.transport_id.send(
                    payload=record._payload_bytes(),
                    filename=record.payload_filename or record.name,
                )
            except Exception as exc:
                _logger.exception(
                    "Outbound %s send failed: %s", record.name, exc,
                )
                record.retry_count += 1
                record.error_message = str(exc)
                if record.retry_count >= record.max_retries:
                    record._transition_state("dead_letter")
                continue
            if result.get("ok"):
                record._transition_state("sent")
                record.sent_at = fields.Datetime.now()
                record.transport_reference = str(result.get("reference") or "")
            else:
                record.retry_count += 1
                record.error_message = str(result.get("error") or "")
                if record.retry_count >= record.max_retries:
                    record._transition_state("dead_letter")

    def action_mark_acked(self):
        self._transition_state("acked")
        for record in self:
            record.acked_at = fields.Datetime.now()

    def action_close(self):
        self._transition_state("closed")

    def action_cancel(self):
        self._transition_state("cancelled")

    def action_resume_dead_letter(self):
        for record in self:
            record.retry_count = 0
            record.error_message = ""
            record._transition_state("queued")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_edi_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-EDI-009] Outbound state must change via the "
                "action buttons."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Translator dispatch
    # ------------------------------------------------------------------
    def _build_payload(self):
        self.ensure_one()
        translator_cls = translator_base.get(
            self.message_type_id.code, "out",
        )
        if not translator_cls:
            raise UserError(_(
                "[EHL-EDI-010] No outbound translator registered "
                "for message type %(code)s."
            ) % {"code": self.message_type_id.code})
        Source = self.env[self.source_model]
        source_record = Source.browse(self.source_id)
        if not source_record.exists():
            raise UserError(_(
                "[EHL-EDI-011] Source record %(model)s/%(id)s no "
                "longer exists; cannot build payload."
            ) % {"model": self.source_model, "id": self.source_id})
        translator = translator_cls(self.env)
        payload_bytes = translator.build(source_record, self.partner_config_id)
        filename = self._render_filename()
        # Persist as base64 because Binary attachment fields expect it.
        import base64
        self.with_context(
            eh_log_edi_internal_payload_write=True,
        ).write({
            "payload": base64.b64encode(payload_bytes),
            "payload_filename": filename,
        })

    def _payload_bytes(self):
        self.ensure_one()
        if not self.payload:
            return b""
        import base64
        return base64.b64decode(self.payload)

    def _render_filename(self):
        self.ensure_one()
        template = (
            self.partner_config_id.filename_template
            or "{message}_{date}_{sequence}.edi"
        )
        return template.format(
            message=self.message_type_id.code,
            date=date.today().strftime("%Y%m%d"),
            sequence=self.name.replace("/", "_"),
            partner_code=self.partner_config_id.partner_identifier or "",
        )

    # ------------------------------------------------------------------
    # Cron entry point
    # ------------------------------------------------------------------
    @api.model
    def cron_dispatch_outbound(self):
        candidates = self.search([("state", "=", "queued")])
        for record in candidates:
            try:
                record.action_send()
            except Exception:
                _logger.exception(
                    "Outbound dispatch failed for %s", record.name,
                )
        return len(candidates)
