# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Customs declaration type master.

Universal types ship in the seed; country localisation packs append
authority-specific variants (e.g. UAE has separate types for "Import
to Local from ROW", "Import to Free Zone", "Transfer FZ to FZ"; KSA
has SABER-required types). The engine never assumes a fixed set.
"""
from odoo import _, api, fields, models


class EhLogCustomsDeclarationType(models.Model):
    _name = "eh.log.customs.declaration.type"
    _description = "Customs Declaration Type"
    _order = "direction, sequence, code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
        help="Stable identifier (IMP, EXP, TRA, TRF, REX, TADM, ...). "
             "Country packs prefix their codes with an ISO country "
             "code (AE-IMP-LOCAL, SA-IMP-SABER, etc.) to namespace "
             "without colliding with the universal codes.",
    )

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )

    sequence = fields.Integer(default=10)

    direction = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
            ("transit", "Transit"),
            ("transfer", "Transfer"),
            ("re_export", "Re-export"),
            ("temporary", "Temporary Admission"),
            ("other", "Other"),
        ],
        string="Direction",
        required=True,
        index=True,
    )

    country_id = fields.Many2one(
        "res.country",
        string="Country",
        index=True,
        help="Optional country scope. Empty means the type applies "
             "globally (used by the universal seed). Country packs "
             "set the country to scope their authority-specific "
             "variants.",
    )

    requires_deferment = fields.Boolean(
        string="Requires Deferment Account",
        help="When True, declarations of this type cannot move past "
             "submitted without a deferment account configured. "
             "Suitable for import declarations where duty must be "
             "paid before release.",
    )

    description = fields.Text(translate=True)

    active = fields.Boolean(default=True)

    _code_country_unique = models.Constraint(
        'UNIQUE(code, country_id)',
        'Declaration type code must be unique per country.',
    )

    @api.depends("code", "name", "country_id")
    def _compute_display_name(self):
        for record in self:
            label = record.name
            if record.country_id:
                label = f"{label} ({record.country_id.code})"
            record.display_name = (
                f"[{record.code}] {label}" if record.code else label
            )
