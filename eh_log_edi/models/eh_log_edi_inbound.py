# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Inbound EDI message queue.

State machine:

    received -> parsed -> processed -> closed
                       \-> rejected

Inbound rows are created by transport adapters or by the receive
endpoint. Each row keeps the raw payload before parse so a parse
failure cannot lose evidence; the rejected state means parse or
apply raised, with the error captured for operator triage.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from ..translators import base as translator_base

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "received": ("parsed", "rejected"),
    "parsed": ("processed", "rejected"),
    "processed": ("closed",),
    "rejected": ("received", "closed"),
    "closed": (),
}


class EhLogEdiInbound(models.Model):
    _name = "eh.log.edi.inbound"
    _description = "EDI Inbound Message"
    _order = "received_at desc, id desc"
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
            ("received", "Received"),
            ("parsed", "Parsed"),
            ("processed", "Processed"),
            ("rejected", "Rejected"),
            ("closed", "Closed"),
        ],
        string="State",
        required=True,
        default="received",
        tracking=True,
        copy=False,
    )
    partner_config_id = fields.Many2one(
        "eh.log.edi.partner",
        string="Partner Configuration",
        required=True,
        ondelete="restrict",
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
    )
    raw_payload = fields.Binary(
        string="Raw Payload",
        attachment=True,
        readonly=True,
    )
    raw_filename = fields.Char(string="Filename", readonly=True)
    parsed_payload = fields.Text(
        string="Parsed Payload",
        readonly=True,
        help=(
            "JSON serialisation of the parser output. Stored for "
            "operator review and replay."
        ),
    )
    received_at = fields.Datetime(
        string="Received At",
        default=fields.Datetime.now,
        required=True,
    )
    parsed_at = fields.Datetime(string="Parsed At", readonly=True)
    processed_at = fields.Datetime(string="Processed At", readonly=True)
    target_record_ref = fields.Char(
        string="Target Record",
        readonly=True,
        help=(
            "Name of the record affected by apply(). For IFTSTA, the "
            "freight job that received the new tracking event."
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
                    "eh.log.edi.inbound"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for inbound in self:
            current = inbound.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Inbound message %(name)s cannot move from "
                      "%(from)s to %(to)s.") % {
                        "name": inbound.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            inbound.with_context(
                eh_log_edi_internal_state_write=True
            ).write({"state": target_state})

    def action_parse(self):
        for record in self:
            translator_cls = translator_base.get(
                record.message_type_id.code, "in",
            )
            if not translator_cls:
                raise UserError(_(
                    "[EHL-EDI-012] No inbound translator registered "
                    "for message type %(code)s."
                ) % {"code": record.message_type_id.code})
            try:
                translator = translator_cls(self.env)
                parsed = translator.parse(
                    record._raw_bytes(),
                    record.partner_config_id,
                )
                import json
                record.parsed_payload = json.dumps(parsed, default=str)
                record._transition_state("parsed")
                record.parsed_at = fields.Datetime.now()
            except Exception as exc:
                _logger.exception(
                    "Inbound %s parse failed: %s", record.name, exc,
                )
                record.error_message = str(exc)
                record._transition_state("rejected")

    def action_process(self):
        import json
        for record in self:
            translator_cls = translator_base.get(
                record.message_type_id.code, "in",
            )
            if not translator_cls:
                raise UserError(_(
                    "[EHL-EDI-013] No inbound translator for "
                    "%(code)s."
                ) % {"code": record.message_type_id.code})
            try:
                translator = translator_cls(self.env)
                parsed = (
                    json.loads(record.parsed_payload)
                    if record.parsed_payload
                    else {}
                )
                target = translator.apply(parsed, record.partner_config_id)
                record._transition_state("processed")
                record.processed_at = fields.Datetime.now()
                if target:
                    record.target_record_ref = (
                        target.display_name if hasattr(target, "display_name") else ""
                    )
            except Exception as exc:
                _logger.exception(
                    "Inbound %s apply failed: %s", record.name, exc,
                )
                record.error_message = str(exc)
                record._transition_state("rejected")

    def action_close(self):
        self._transition_state("closed")

    def action_resume(self):
        for record in self:
            record.error_message = ""
            record._transition_state("received")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_edi_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-EDI-014] Inbound state must change via the "
                "action buttons."
            ))
        return super().write(vals)

    def _raw_bytes(self):
        self.ensure_one()
        if not self.raw_payload:
            return b""
        import base64
        return base64.b64decode(self.raw_payload)

    # ------------------------------------------------------------------
    # External entry point
    # ------------------------------------------------------------------
    @api.model
    def receive(self, partner_config, message_type, payload_bytes, filename=None):
        """Persist an inbound payload and set it to received state."""
        import base64
        record = self.create({
            "partner_config_id": partner_config.id,
            "message_type_id": message_type.id,
            "raw_payload": base64.b64encode(payload_bytes),
            "raw_filename": filename or "",
            "received_at": fields.Datetime.now(),
            "company_id": partner_config.company_id.id,
        })
        return record

    # ------------------------------------------------------------------
    # Cron entry point
    # ------------------------------------------------------------------
    @api.model
    def cron_process_inbound(self):
        candidates = self.search([("state", "=", "received")])
        for record in candidates:
            record.action_parse()
            if record.state == "parsed":
                record.action_process()
        return len(candidates)
