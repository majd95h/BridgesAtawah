# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Carrier lane filter.

A lane row says "this carrier serves this origin/destination/mode
pair." Rate-shop walks the lanes per carrier and skips a carrier
that does not serve the requested route. Without lanes the rate-shop
fan-out hits every active carrier; with lanes it stays focused.

Origins and destinations are country codes plus optional location
codes. A blank location matches any location in the named country
(useful for "we serve all of UAE for ocean").
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EhLogCarrierLane(models.Model):
    _name = "eh.log.carrier.lane"
    _description = "Carrier Lane"
    _order = "carrier_profile_id, origin_country_id, destination_country_id"

    carrier_profile_id = fields.Many2one(
        "eh.log.carrier.profile",
        string="Carrier",
        required=True,
        ondelete="cascade",
        index=True,
    )
    mode = fields.Selection(
        related="carrier_profile_id.mode",
        store=True,
        readonly=True,
    )
    origin_country_id = fields.Many2one(
        "res.country",
        string="Origin Country",
        required=True,
    )
    origin_location_code = fields.Char(
        string="Origin Location Code",
        help=(
            "UN/LOCODE or carrier-specific port/airport code. Blank "
            "matches any location in the origin country."
        ),
    )
    destination_country_id = fields.Many2one(
        "res.country",
        string="Destination Country",
        required=True,
    )
    destination_location_code = fields.Char(
        string="Destination Location Code",
    )
    transit_days_min = fields.Integer(
        string="Transit Days Min",
        default=0,
    )
    transit_days_max = fields.Integer(
        string="Transit Days Max",
        default=0,
    )
    company_id = fields.Many2one(
        related="carrier_profile_id.company_id",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    @api.constrains("transit_days_min", "transit_days_max")
    def _check_transit_range(self):
        for lane in self:
            if lane.transit_days_max and lane.transit_days_min > lane.transit_days_max:
                raise ValidationError(_(
                    "[EHL-CAR-003] Lane transit minimum %(min)s "
                    "exceeds maximum %(max)s."
                ) % {
                    "min": lane.transit_days_min,
                    "max": lane.transit_days_max,
                })

    def matches(self, origin_country_code, destination_country_code,
                origin_location_code=None, destination_location_code=None):
        """Return True if this lane serves the requested route."""
        self.ensure_one()
        if (self.origin_country_id.code or "").upper() != (origin_country_code or "").upper():
            return False
        if (self.destination_country_id.code or "").upper() != (destination_country_code or "").upper():
            return False
        if self.origin_location_code:
            if (origin_location_code or "").upper() != self.origin_location_code.upper():
                return False
        if self.destination_location_code:
            if (destination_location_code or "").upper() != self.destination_location_code.upper():
                return False
        return True
