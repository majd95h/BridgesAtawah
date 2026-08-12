# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Lightweight vehicle master.

Sufficient for the road transport core. Deeper fleet management
(maintenance, fuel cards, telematics, hours-of-service) integrates
through a dedicated fleet module that links each
``eh.log.transport.vehicle`` to a ``fleet.vehicle`` record when the
``fleet`` module is also installed.
"""
from odoo import _, api, fields, models


class EhLogTransportVehicle(models.Model):
    _name = "eh.log.transport.vehicle"
    _description = "Transport Vehicle"
    _order = "registration"
    _rec_names_search = ["registration", "name"]

    registration = fields.Char(
        string="Registration",
        required=True,
        index=True,
    )

    name = fields.Char(
        string="Name",
        required=True,
        help="Operator-friendly label, e.g. 'Volvo FH16 #3'.",
    )

    vehicle_type = fields.Selection(
        selection=[
            ("rigid", "Rigid Truck"),
            ("tractor", "Tractor Unit"),
            ("trailer", "Trailer"),
            ("rigid_box", "Rigid Box"),
            ("tipper", "Tipper"),
            ("tanker", "Tanker"),
            ("flatbed", "Flatbed"),
            ("reefer", "Reefer Trailer"),
            ("low_bed", "Low Bed"),
            ("van", "Van"),
            ("other", "Other"),
        ],
        string="Type",
        default="rigid",
        required=True,
        index=True,
    )

    capacity_payload_kg = fields.Float(string="Payload (kg)")

    capacity_volume_cbm = fields.Float(string="Volume (m3)")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_transport_vehicle_company_rel",
        "vehicle_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    home_depot_id = fields.Many2one(
        "res.partner",
        string="Home Depot",
        help="Optional. Used by route planning to bias trip start "
             "and finish points.",
    )

    notes = fields.Text(string="Notes")

    active = fields.Boolean(default=True)

    _registration_company_unique = models.Constraint(
        'UNIQUE(registration, company_id)',
        'Vehicle registration must be unique per company.',
    )

    @api.depends("company_id")
    def _compute_company_ids(self):
        for vehicle in self:
            vehicle.company_ids = vehicle.company_id

    @api.depends("registration", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.registration}] {record.name}"
                if record.registration else record.name
            )
