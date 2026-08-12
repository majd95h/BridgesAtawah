# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Warehouse location master.

The addressable bin: the smallest unit a movement can target. The
composite reference ``<facility>/<zone>/<code>`` is what appears on
labels and pick lists, so the three-part code stays short.

Locations have a per-bin pallet capacity and a current pallet count
derived from the movement log. The current count is a stored compute
that invalidates on movement create; it is not authoritative for
billing (the daily snapshot is) but it is authoritative for live
put-away decisions.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EhLogWarehouseLocation(models.Model):
    _name = "eh.log.warehouse.location"
    _description = "Warehouse Location"
    _order = "zone_id, code"
    _rec_names_search = ["full_code", "code"]

    name = fields.Char(string="Name")
    code = fields.Char(string="Code", required=True, size=12)
    full_code = fields.Char(
        string="Full Code",
        compute="_compute_full_code",
        store=True,
        index=True,
        help=(
            "Composite location reference of facility code, zone "
            "code, and location code joined by slashes. Printed on "
            "labels and pick lists."
        ),
    )
    zone_id = fields.Many2one(
        "eh.log.warehouse.zone",
        string="Zone",
        required=True,
        ondelete="restrict",
        index=True,
    )
    facility_id = fields.Many2one(
        related="zone_id.facility_id",
        store=True,
        index=True,
    )
    purpose = fields.Selection(
        related="zone_id.purpose",
        store=True,
    )
    pallet_capacity = fields.Integer(
        string="Pallet Capacity",
        default=1,
        help=(
            "Per-bin pallet ceiling. Put-away above this triggers a "
            "warning but does not block; over-capacity is a valid "
            "transient state."
        ),
    )
    pallets_on_hand = fields.Integer(
        string="Pallets On Hand",
        compute="_compute_pallets_on_hand",
        store=True,
        help=(
            "Live pallet count derived from the movement log. "
            "Authoritative for put-away decisions; storage billing "
            "uses the daily snapshot instead."
        ),
    )

    inbound_movement_ids = fields.One2many(
        "eh.log.warehouse.movement",
        "destination_location_id",
        string="Inbound Movements",
    )
    outbound_movement_ids = fields.One2many(
        "eh.log.warehouse.movement",
        "source_location_id",
        string="Outbound Movements",
    )
    company_id = fields.Many2one(
        related="zone_id.company_id",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _location_code_unique = models.Constraint(
        'unique(zone_id, code)',
        'Location code must be unique per zone.',
    )

    @api.depends("zone_id.facility_id.code", "zone_id.code", "code")
    def _compute_full_code(self):
        for location in self:
            facility_code = location.zone_id.facility_id.code or ""
            zone_code = location.zone_id.code or ""
            location.full_code = "/".join(
                part for part in [facility_code, zone_code, location.code]
                if part
            )

    @api.depends("inbound_movement_ids.pallet_count",
                 "outbound_movement_ids.pallet_count")
    def _compute_pallets_on_hand(self):
        # Depend on the movement relations (not zone_id) so the stored
        # value recomputes whenever a put-away or pick movement touches
        # the location, instead of staying frozen at its create-time zero.
        for location in self:
            inbound = sum(location.inbound_movement_ids.mapped("pallet_count"))
            outbound = sum(location.outbound_movement_ids.mapped("pallet_count"))
            location.pallets_on_hand = inbound - outbound

    @api.constrains("code")
    def _check_code_format(self):
        for location in self:
            if not location.code or not location.code.replace("_", "").isalnum():
                raise ValidationError(_(
                    "[EHL-WHS-003] Location code %(code)s must be "
                    "alphanumeric or underscore only."
                ) % {"code": location.code})
