# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Oman customs offices master."""
from odoo import _, api, fields, models


class EhLogL10nOmCustomsOffice(models.Model):
    _name = "eh.log.l10n.om.customs.office"
    _description = "Oman Customs Office"
    _order = "is_authority desc, name"
    _rec_names_search = ["code", "name"]

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string="Name", required=True, translate=True)
    office_kind = fields.Selection(
        selection=[
            ("customs_authority", "Customs Authority"),
            ("port_customs_house", "Port Customs House"),
            ("airport_customs_house", "Airport Customs House"),
            ("tax_authority", "Tax Authority"),
        ],
        string="Office Kind",
        required=True,
        default="customs_authority",
    )
    is_authority = fields.Boolean(
        string="Is Authority",
        compute="_compute_is_authority",
        store=True,
    )
    parent_authority_id = fields.Many2one(
        "eh.log.l10n.om.customs.office",
        string="Parent Authority",
        ondelete="restrict",
    )
    single_window_url = fields.Char(string="Single Window URL")
    helpline_phone = fields.Char(string="Helpline Phone")
    notes = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'Customs office code must be unique.',
    )

    @api.depends("office_kind")
    def _compute_is_authority(self):
        for record in self:
            record.is_authority = record.office_kind in ("customs_authority", "tax_authority")

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.code}] {record.name}" if record.code else record.name
            )
