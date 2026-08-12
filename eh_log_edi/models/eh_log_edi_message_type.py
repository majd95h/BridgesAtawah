# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""EDI message type master.

A message type is one row per EDIFACT or X12 message identifier the
operator wants to support. Out-of-the-box rows ship via config data;
operators add custom rows for partner-specific extensions.

The translator field is a free-text key matched against the
translator registry; the field is validated at save time so a typo
surfaces before a dispatch attempt.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from ..translators import base as translator_base


class EhLogEdiMessageType(models.Model):
    _name = "eh.log.edi.message.type"
    _description = "EDI Message Type"
    _order = "encoding, code"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True, size=12)
    direction = fields.Selection(
        [
            ("out", "Outbound"),
            ("in", "Inbound"),
            ("both", "Both"),
        ],
        string="Direction",
        required=True,
        default="both",
    )
    encoding = fields.Selection(
        [
            ("edifact", "UN/EDIFACT"),
            ("x12", "ANSI X12"),
            ("xml", "XML"),
            ("json", "JSON"),
        ],
        string="Encoding",
        required=True,
        default="edifact",
    )
    description = fields.Text(string="Description", translate=True)
    active = fields.Boolean(default=True)

    _code_direction_unique = models.Constraint(
        'unique(code, direction)',
        'Message type code/direction combination must be unique.',
    )

    @api.constrains("code", "direction")
    def _check_translator_registered(self):
        for message_type in self:
            if not message_type.active:
                continue
            for direction in self._directions(message_type.direction):
                translator = translator_base.get(message_type.code, direction)
                if not translator:
                    raise ValidationError(_(
                        "[EHL-EDI-001] No translator registered for "
                        "message type %(code)s direction %(direction)s. "
                        "Install the module that provides the "
                        "translator or untick Active."
                    ) % {
                        "code": message_type.code,
                        "direction": direction,
                    })

    @staticmethod
    def _directions(direction):
        if direction == "both":
            return ("out", "in")
        return (direction,)
