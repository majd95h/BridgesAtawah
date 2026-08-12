# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Husbandry service catalog.

A husbandry service is anything the ship agent arranges on behalf of
the vessel that is not core port-authority charges: crew change
transport, ship spares clearance, fresh water, garbage removal, slop
reception, bunker coordination, ship chandlery delivery.

Each entry carries a default charge code (from eh_log_base) so the
disbursement account picks up rates from the existing rate sheet
mechanism rather than maintaining a parallel pricing table.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Closed enum for the husbandry category. Used to filter the catalog
# in the disbursement-account form so the agent picks from a focused
# list per call type.
HUSBANDRY_CATEGORIES = [
    ("crew_change", "Crew Change"),
    ("spares", "Ship Spares"),
    ("provisions", "Provisions / Chandlery"),
    ("fresh_water", "Fresh Water"),
    ("garbage", "Garbage Removal"),
    ("slop", "Slop Reception"),
    ("bunker", "Bunker Coordination"),
    ("medical", "Medical"),
    ("other", "Other"),
]


class EhLogShipHusbandryService(models.Model):
    _name = "eh.log.ship.husbandry.service"
    _description = "Husbandry Service"
    _order = "category, name"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True, size=12)
    category = fields.Selection(
        HUSBANDRY_CATEGORIES,
        string="Category",
        required=True,
    )
    charge_code_id = fields.Many2one(
        "eh.log.charge.code",
        string="Default Charge Code",
        ondelete="restrict",
        help=(
            "Default charge code used when this service appears on a "
            "disbursement account. The DA can still override per "
            "line if a specific call needs a different code."
        ),
    )
    description = fields.Text(string="Description", translate=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _husbandry_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Husbandry service code must be unique per company.',
    )
