# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Oman sea ports master with UN/LOCODE references."""
from odoo import _, api, fields, models


class EhLogL10nOmPort(models.Model):
    _name = "eh.log.l10n.om.port"
    _description = "Oman Sea Port"
    _order = "name"
    _rec_names_search = ["unlocode", "name"]

    name = fields.Char(string="Name", required=True, translate=True)
    unlocode = fields.Char(string="UN/LOCODE", required=True, index=True, size=5)
    operator_name = fields.Char(string="Operator")
    container_terminal = fields.Boolean(string="Container Terminal", default=True)
    bulk_terminal = fields.Boolean(string="Bulk Terminal")
    petrochemical = fields.Boolean(string="Petrochemical")
    notes = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _unlocode_unique = models.Constraint(
        'UNIQUE(unlocode)',
        'UN/LOCODE must be unique.',
    )

    @api.depends("name", "unlocode")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.unlocode}] {record.name}"
                if record.unlocode else record.name
            )
