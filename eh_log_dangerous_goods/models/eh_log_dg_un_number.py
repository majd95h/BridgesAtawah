# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""UN number master.

The 4-digit UN number identifies a specific dangerous substance or
article. Carries the proper shipping name, primary hazard class,
subsidiary risks, packing group, marine pollutant flag, and per-mode
notes (IMDG, IATA, ADR).

Production deployments load the full UN dangerous-goods list (about
3000 entries) via a separate data load supplied by the customer's DG
data partner. The seed here covers the most common entries so
operators can start filing declarations on day one.
"""
import re

from odoo import _, api, fields, models

from odoo.addons.eh_log_base.exceptions import EhLogValidationError


UN_NUMBER_RE = re.compile(r"^UN\d{4}$")


class EhLogDgUnNumber(models.Model):
    _name = "eh.log.dg.un.number"
    _description = "UN Dangerous Goods Number"
    _order = "un_number"
    _rec_names_search = ["un_number", "proper_shipping_name"]

    un_number = fields.Char(
        string="UN Number",
        required=True,
        index=True,
        size=6,
        help="Format: UN followed by 4 digits, e.g. UN1090.",
    )

    proper_shipping_name = fields.Char(
        string="Proper Shipping Name",
        required=True,
        translate=True,
        index="trigram",
    )

    primary_class_id = fields.Many2one(
        "eh.log.dg.class",
        string="Primary Class",
        required=True,
        ondelete="restrict",
        index=True,
    )

    subsidiary_class_ids = fields.Many2many(
        "eh.log.dg.class",
        "eh_log_dg_un_number_subsidiary_class_rel",
        "un_id",
        "class_id",
        string="Subsidiary Risks",
    )

    packing_group = fields.Selection(
        selection=[
            ("I", "I (High danger)"),
            ("II", "II (Medium danger)"),
            ("III", "III (Low danger)"),
            ("none", "Not applicable"),
        ],
        string="Packing Group",
        default="none",
        required=True,
    )

    marine_pollutant = fields.Boolean(
        string="Marine Pollutant",
        default=False,
        help="Required IMDG flag for substances harmful to marine life.",
    )

    flashpoint_celsius = fields.Float(
        string="Flashpoint (degC)",
        digits=(6, 2),
        help="Required for class 3 entries on IATA DGR and IMDG.",
    )

    ems_code = fields.Char(
        string="EmS Code",
        help="IMDG Emergency Schedule code (e.g. F-E, S-V).",
    )

    imdg_special_provisions = fields.Char(string="IMDG Special Provisions")
    iata_special_provisions = fields.Char(string="IATA Special Provisions")
    adr_special_provisions = fields.Char(string="ADR Special Provisions")

    iata_passenger_aircraft_forbidden = fields.Boolean(
        string="Forbidden on Passenger Aircraft",
        default=False,
    )
    iata_cargo_aircraft_forbidden = fields.Boolean(
        string="Forbidden on Cargo Aircraft",
        default=False,
    )

    description = fields.Text(translate=True)

    active = fields.Boolean(default=True)

    _un_number_unique = models.Constraint(
        'UNIQUE(un_number)',
        'UN number must be unique.',
    )

    @api.constrains("un_number")
    def _check_un_number_format(self):
        for record in self:
            if not UN_NUMBER_RE.match((record.un_number or "").upper()):
                raise EhLogValidationError(
                    130,
                    _(
                        "UN number %(un)s does not match the required "
                        "format. Use 'UN' followed by 4 digits, e.g. "
                        "UN1090."
                    ) % {"un": record.un_number},
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("un_number"):
                vals["un_number"] = vals["un_number"].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("un_number"):
            vals["un_number"] = vals["un_number"].strip().upper()
        return super().write(vals)

    @api.depends("un_number", "proper_shipping_name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"{record.un_number} {record.proper_shipping_name}"
                if record.un_number else record.proper_shipping_name
            )
