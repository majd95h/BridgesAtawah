# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Warehouse zone master.

A zone is one section of a facility with a single purpose: bonded,
free, transit, staging, quarantine. Picks and put-aways within the
same zone bypass customs interaction; cross-zone moves into bonded
require a declaration link.

The zone purpose is enforced at movement creation time: bonded
material cannot land in staging without an audit trail.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Zones serving as physical inventory must be one of the following.
# The list is closed; adding a new purpose requires also extending
# the movement validation rules so the system rejects ambiguous
# transitions.
PHYSICAL_ZONE_PURPOSES = (
    "bonded",
    "free",
    "domestic",
    "quarantine",
)


class EhLogWarehouseZone(models.Model):
    _name = "eh.log.warehouse.zone"
    _description = "Warehouse Zone"
    _order = "facility_id, code"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True, size=8)
    facility_id = fields.Many2one(
        "eh.log.warehouse.facility",
        string="Facility",
        required=True,
        ondelete="restrict",
        index=True,
    )
    purpose = fields.Selection(
        [
            ("bonded", "Bonded"),
            ("free", "Free Zone"),
            ("domestic", "Domestic"),
            ("staging", "Staging"),
            ("quarantine", "Quarantine"),
            ("transit", "Transit"),
        ],
        string="Purpose",
        required=True,
        default="domestic",
        help=(
            "Drives movement validation. Bonded zones require a "
            "customs declaration on inbound; free zones require a "
            "domestic-customs entry on outbound to a non-free "
            "destination."
        ),
    )
    location_ids = fields.One2many(
        "eh.log.warehouse.location",
        "zone_id",
        string="Locations",
    )
    location_count = fields.Integer(
        string="Locations",
        compute="_compute_location_count",
    )
    company_id = fields.Many2one(
        related="facility_id.company_id",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _zone_code_unique = models.Constraint(
        'unique(facility_id, code)',
        'Zone code must be unique per facility.',
    )

    @api.depends("location_ids")
    def _compute_location_count(self):
        for zone in self:
            zone.location_count = len(zone.location_ids)

    @api.constrains("code")
    def _check_code_format(self):
        for zone in self:
            if not zone.code or not zone.code.replace("_", "").isalnum():
                raise ValidationError(_(
                    "[EHL-WHS-002] Zone code %(code)s must be "
                    "alphanumeric or underscore only."
                ) % {"code": zone.code})

    def action_view_locations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Locations"),
            "res_model": "eh.log.warehouse.location",
            "view_mode": "list,form",
            "domain": [("zone_id", "=", self.id)],
            "context": {"default_zone_id": self.id},
        }
