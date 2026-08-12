# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""DG declaration line: per UN number on the shipment."""
from odoo import _, api, fields, models


class EhLogDgDeclarationLine(models.Model):
    _name = "eh.log.dg.declaration.line"
    _description = "DG Declaration Line"
    _order = "declaration_id, sequence, id"
    _rec_name = "un_number_id"

    declaration_id = fields.Many2one(
        "eh.log.dg.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sequence = fields.Integer(default=10)

    un_number_id = fields.Many2one(
        "eh.log.dg.un.number",
        string="UN Number",
        required=True,
        index=True,
    )

    primary_class = fields.Char(
        string="Primary Class",
        related="un_number_id.primary_class_id.code",
        store=True,
        readonly=True,
    )

    packing_group = fields.Selection(
        related="un_number_id.packing_group",
        store=True,
        readonly=True,
    )

    marine_pollutant = fields.Boolean(
        related="un_number_id.marine_pollutant",
        store=True,
        readonly=True,
    )

    technical_name = fields.Char(
        string="Technical Name",
        help="Required when the proper shipping name is generic "
             "(e.g. 'Flammable liquid n.o.s.'). The technical name "
             "appears in parentheses on the printed declaration.",
    )

    packaging_description = fields.Char(
        string="Packaging",
        required=True,
        help="Free-form packaging description, e.g. '20 fibreboard "
             "boxes, 1 L each'.",
    )

    package_count = fields.Integer(string="Packages", default=1)

    net_quantity = fields.Float(
        string="Net Quantity",
        required=True,
        help="Net quantity per package. Multiplied by package count "
             "to derive the gross quantity printed on the declaration.",
    )

    net_quantity_uom = fields.Selection(
        selection=[
            ("kg", "kg"),
            ("g", "g"),
            ("L", "L"),
            ("mL", "mL"),
            ("PCS", "pieces"),
        ],
        string="UoM",
        default="kg",
        required=True,
    )

    total_quantity = fields.Float(
        string="Total Quantity",
        compute="_compute_total_quantity",
        store=True,
    )

    notes = fields.Char(string="Notes")

    @api.depends("net_quantity", "package_count")
    def _compute_total_quantity(self):
        for line in self:
            line.total_quantity = (line.net_quantity or 0.0) * (line.package_count or 0)

    @api.onchange("un_number_id")
    def _onchange_un_number_id(self):
        if self.un_number_id and self.un_number_id.proper_shipping_name:
            shipping_name = self.un_number_id.proper_shipping_name
            if "n.o.s." in shipping_name.lower() and not self.technical_name:
                # Hint to the user that a technical name is required.
                return {
                    "warning": {
                        "title": "Technical name required",
                        "message": (
                            f"{self.un_number_id.un_number} "
                            f"({shipping_name}) is a generic 'n.o.s.' "
                            f"entry. The IMDG and IATA DGR require a "
                            f"technical name in parentheses on the "
                            f"declaration. Set the Technical Name field."
                        ),
                    },
                }
