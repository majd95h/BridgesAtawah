# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""IMDG / IATA / ADR hazard class catalogue.

The nine UN hazard classes plus subdivisions. A separate model rather
than a Selection so country packs and customers can append niche
sub-classifications (e.g. lithium battery sub-codes UN3480 vs UN3481)
without forking the engine.

Each row also documents IMDG segregation incompatibilities as a
many-to-many to other classes. The DG declaration's segregation
detector reads from this catalogue.
"""
from odoo import _, api, fields, models


class EhLogDgClass(models.Model):
    _name = "eh.log.dg.class"
    _description = "Dangerous Goods Hazard Class"
    _order = "code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(
        string="Class Code",
        required=True,
        index=True,
        help="UN hazard class code, e.g. '1', '1.1', '2.1', '4.3'.",
    )

    name = fields.Char(string="Name", required=True, translate=True)

    primary_class = fields.Selection(
        selection=[
            ("1", "1 Explosives"),
            ("2", "2 Gases"),
            ("3", "3 Flammable Liquids"),
            ("4", "4 Flammable Solids and Self-Reactive"),
            ("5", "5 Oxidising Substances and Organic Peroxides"),
            ("6", "6 Toxic and Infectious Substances"),
            ("7", "7 Radioactive Material"),
            ("8", "8 Corrosive Substances"),
            ("9", "9 Miscellaneous Dangerous Substances"),
        ],
        string="Primary Class",
        required=True,
        index=True,
    )

    placard_description = fields.Char(
        string="Placard Description",
        translate=True,
        help="Short text printed on the orange placard.",
    )

    stowage_notes = fields.Text(translate=True)

    incompatible_class_ids = fields.Many2many(
        "eh.log.dg.class",
        "eh_log_dg_class_incompatibility_rel",
        "class_id",
        "incompatible_id",
        string="Incompatible Classes",
        help="Classes that cannot share a transport unit with this "
             "class without specific segregation. Drives the "
             "segregation detector on the declaration.",
    )

    description = fields.Text(translate=True)

    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'Hazard class code must be unique.',
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.code}] {record.name}" if record.code else record.name
            )
