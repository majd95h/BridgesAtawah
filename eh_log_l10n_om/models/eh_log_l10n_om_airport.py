# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Oman airports master with IATA codes."""
from odoo import _, api, fields, models


class EhLogL10nOmAirport(models.Model):
    _name = "eh.log.l10n.om.airport"
    _description = "Oman Airport"
    _order = "name"
    _rec_names_search = ["iata_code", "name"]

    name = fields.Char(string="Name", required=True, translate=True)
    iata_code = fields.Char(string="IATA Code", required=True, index=True, size=3)
    icao_code = fields.Char(string="ICAO Code", size=4)
    cargo_capable = fields.Boolean(string="Cargo Capable", default=True)
    notes = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _iata_code_unique = models.Constraint(
        'UNIQUE(iata_code)',
        'IATA code must be unique.',
    )

    @api.depends("name", "iata_code")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.iata_code}] {record.name}"
                if record.iata_code else record.name
            )
