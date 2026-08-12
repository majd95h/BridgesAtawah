# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Oman free zones master."""
from odoo import _, api, fields, models


class EhLogL10nOmFreeZone(models.Model):
    _name = "eh.log.l10n.om.free.zone"
    _description = "Oman Free Zone"
    _order = "code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(string="Code", required=True, index=True)
    name = fields.Char(string="Name", required=True, translate=True)
    is_bonded = fields.Boolean(string="Bonded Zone", default=True)
    regulator_name = fields.Char(string="Regulating Authority", translate=True)
    website = fields.Char(string="Website")
    notes = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'Free zone code must be unique.',
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.code}] {record.name}" if record.code else record.name
            )
