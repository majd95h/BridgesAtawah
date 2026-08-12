# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Warehouse facility master.

A facility is one physical building (or a contiguous parcel) that the
3PL operates. Carries the customs classification: bonded, free zone,
or transit. The classification drives downstream behaviour: a bonded
facility's receipt requires a customs declaration reference; a free
zone facility's pick triggers a domestic-customs entry instead.

Facilities aggregate zones; zones aggregate locations; locations are
the addressable bins. A movement always points to a location, never
straight to the facility, so on-hand calculations roll up through
the hierarchy without ambiguity.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EhLogWarehouseFacility(models.Model):
    _name = "eh.log.warehouse.facility"
    _description = "Warehouse Facility"
    _order = "code, name"
    _rec_names_search = ["name", "code"]
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        size=8,
        tracking=True,
        help=(
            "Short code prefixed onto location codes. Limit eight "
            "characters so the composite location reference fits a "
            "label sticker."
        ),
    )
    customs_status = fields.Selection(
        [
            ("bonded", "Bonded"),
            ("free_zone", "Free Zone"),
            ("transit", "Transit"),
            ("domestic", "Domestic"),
        ],
        string="Customs Status",
        required=True,
        default="domestic",
        tracking=True,
    )
    address_id = fields.Many2one(
        "res.partner",
        string="Address",
        domain="[('is_company', '=', True)]",
        help=(
            "Partner record carrying the street, city, country, and "
            "geo coordinates. Reused on receipts and picks to render "
            "the facility address on documents."
        ),
    )
    total_pallet_capacity = fields.Integer(
        string="Pallet Capacity",
        help=(
            "Operator-supplied design capacity. Reported as a "
            "utilisation percentage on the dashboard but does not "
            "block put-away above the threshold; over-capacity is a "
            "valid temporary state during a peak."
        ),
    )
    zone_ids = fields.One2many(
        "eh.log.warehouse.zone",
        "facility_id",
        string="Zones",
    )
    zone_count = fields.Integer(
        string="Zones",
        compute="_compute_zone_count",
    )
    location_count = fields.Integer(
        string="Locations",
        compute="_compute_location_count",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _facility_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Facility code must be unique per company.',
    )

    @api.depends("zone_ids")
    def _compute_zone_count(self):
        for facility in self:
            facility.zone_count = len(facility.zone_ids)

    def _compute_location_count(self):
        Location = self.env["eh.log.warehouse.location"]
        for facility in self:
            facility.location_count = Location.search_count([
                ("zone_id.facility_id", "=", facility.id),
            ])

    @api.constrains("code")
    def _check_code_format(self):
        for facility in self:
            if not facility.code:
                continue
            if not facility.code.replace("_", "").isalnum():
                raise ValidationError(_(
                    "[EHL-WHS-001] Facility code %(code)s must be "
                    "alphanumeric or underscore only."
                ) % {"code": facility.code})

    def action_view_zones(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Zones"),
            "res_model": "eh.log.warehouse.zone",
            "view_mode": "list,form",
            "domain": [("facility_id", "=", self.id)],
            "context": {"default_facility_id": self.id},
        }
