# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Per-partner EDI configuration.

A partner-config row pairs a res.partner with a transport, a list of
supported message types, and a partner identifier (GLN, DUNS, EAN,
or internal). The configuration drives every dispatch decision: which
transport, which file naming, which version of the message type.

A partner can have multiple configurations to support different
contracts (e.g., production + staging), but only one is allowed to
be the default for a given message type at a time.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


# Default file naming template. {message} {date} {sequence} are
# substituted at send time. Operators can override per configuration
# to match the partner's required convention.
DEFAULT_FILENAME_TEMPLATE = "{message}_{date}_{sequence}.edi"


class EhLogEdiPartner(models.Model):
    _name = "eh.log.edi.partner"
    _description = "EDI Partner Configuration"
    _order = "partner_id, name"
    _rec_names_search = ["name", "partner_identifier"]
    _inherit = ["mail.thread"]

    name = fields.Char(string="Name", required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    partner_identifier = fields.Char(
        string="Partner Identifier",
        required=True,
        tracking=True,
        help=(
            "GLN, DUNS, EAN, or internal code carried in the EDI "
            "envelope as the recipient identifier."
        ),
    )
    self_party_identifier_override = fields.Char(
        string="Self Identifier Override",
        help=(
            "Identifier the partner expects to see as the sender. "
            "Falls back to the company's eh_log_edi_self_identifier "
            "when blank."
        ),
    )
    transport_id = fields.Many2one(
        "eh.log.edi.transport",
        string="Transport",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    message_type_ids = fields.Many2many(
        "eh.log.edi.message.type",
        "eh_log_edi_partner_message_type_rel",
        "partner_id",
        "message_type_id",
        string="Message Types",
        help=(
            "Message types this configuration may dispatch / receive."
        ),
    )
    filename_template = fields.Char(
        string="Filename Template",
        default=DEFAULT_FILENAME_TEMPLATE,
        required=True,
        help=(
            "Substitutions: {message}, {date}, {sequence}, "
            "{partner_code}. Used to compose outbound filenames."
        ),
    )
    is_default = fields.Boolean(
        string="Default for Partner",
        default=False,
        help=(
            "Pick this configuration when the dispatcher needs to "
            "send to the partner without an explicit configuration "
            "reference."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True, tracking=True)

    _partner_identifier_unique = models.Constraint(
        'unique(partner_id, partner_identifier, company_id)',
        'Duplicate partner identifier for the same partner.',
    )

    @api.constrains("is_default")
    def _check_single_default(self):
        for record in self:
            if not record.is_default:
                continue
            duplicates = self.search([
                ("partner_id", "=", record.partner_id.id),
                ("is_default", "=", True),
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
            ])
            if duplicates:
                raise ValidationError(_(
                    "[EHL-EDI-008] Only one default EDI "
                    "configuration is allowed per partner."
                ))

    def _self_party_identifier(self):
        """Identifier the dispatcher uses as 'sender' for this config."""
        self.ensure_one()
        if self.self_party_identifier_override:
            return self.self_party_identifier_override
        Param = self.env["ir.config_parameter"].sudo()
        configured = Param.get_param("eh_log_edi.self_identifier")
        return configured or self.company_id.partner_id.ref or "ERPHERITAGE"

    def queue_outbound(self, message_type, source_record):
        """Create a queued outbound row for this partner / message."""
        self.ensure_one()
        Outbound = self.env["eh.log.edi.outbound"]
        return Outbound.create({
            "partner_config_id": self.id,
            "message_type_id": message_type.id,
            "source_model": source_record._name,
            "source_id": source_record.id,
            "company_id": self.company_id.id,
        })
