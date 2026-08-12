# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Convoy plan and per-vehicle assignments.

A convoy is one move on one route on one day with one set of
vehicles. A job often spawns several convoys (one per oversized
piece, sometimes one per leg of the route). Each convoy aggregates
vehicle assignments, links to the route survey it follows, and
references the permits it requires.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EhLogProjectCargoConvoy(models.Model):
    _name = "eh.log.project.cargo.convoy"
    _description = "Project Cargo Convoy"
    _order = "scheduled_departure desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    job_id = fields.Many2one(
        "eh.log.project.cargo.job",
        string="Job",
        required=True,
        ondelete="cascade",
        index=True,
    )
    item_ids = fields.Many2many(
        "eh.log.project.cargo.item",
        "eh_log_pcg_convoy_item_rel",
        "convoy_id",
        "item_id",
        string="Items Carried",
        domain="[('job_id', '=', job_id)]",
    )
    route_survey_id = fields.Many2one(
        "eh.log.project.cargo.route.survey",
        string="Route Survey",
        ondelete="restrict",
        domain="[('job_id', '=', job_id)]",
    )
    scheduled_departure = fields.Datetime(string="Scheduled Departure")
    scheduled_arrival = fields.Datetime(string="Scheduled Arrival")
    actual_departure = fields.Datetime(string="Actual Departure", readonly=True)
    actual_arrival = fields.Datetime(string="Actual Arrival", readonly=True)
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("in_transit", "In Transit"),
            ("arrived", "Arrived"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="planned",
        required=True,
        tracking=True,
    )
    vehicle_ids = fields.One2many(
        "eh.log.project.cargo.convoy.vehicle",
        "convoy_id",
        string="Vehicles",
    )
    vehicle_count = fields.Integer(
        string="Vehicles",
        compute="_compute_vehicle_count",
        store=True,
    )
    has_lifting_equipment = fields.Boolean(
        string="Has Lifting Equipment",
        compute="_compute_has_lifting_equipment",
        store=True,
    )
    has_escort_vehicle = fields.Boolean(
        string="Has Escort Vehicle",
        compute="_compute_has_escort_vehicle",
        store=True,
    )
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one(
        related="job_id.company_id",
        store=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.project.cargo.convoy"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("vehicle_ids")
    def _compute_vehicle_count(self):
        for convoy in self:
            convoy.vehicle_count = len(convoy.vehicle_ids)

    @api.depends("vehicle_ids.equipment_id.equipment_type")
    def _compute_has_lifting_equipment(self):
        lifting_types = (
            "crane_mobile", "crane_crawler", "crane_telescopic",
            "crane_gantry",
        )
        for convoy in self:
            convoy.has_lifting_equipment = any(
                v.equipment_id.equipment_type in lifting_types
                for v in convoy.vehicle_ids
            )

    @api.depends("vehicle_ids.equipment_id.equipment_type")
    def _compute_has_escort_vehicle(self):
        for convoy in self:
            convoy.has_escort_vehicle = any(
                v.equipment_id.equipment_type == "escort"
                for v in convoy.vehicle_ids
            )

    @api.constrains("scheduled_departure", "scheduled_arrival")
    def _check_schedule_order(self):
        for convoy in self:
            if (convoy.scheduled_departure and convoy.scheduled_arrival
                    and convoy.scheduled_arrival < convoy.scheduled_departure):
                raise ValidationError(_(
                    "[EHL-PCG-008] Convoy %(name)s scheduled "
                    "arrival is before scheduled departure."
                ) % {"name": convoy.name})

    def action_mark_in_transit(self):
        for convoy in self:
            if not convoy.vehicle_ids:
                raise UserError(_(
                    "[EHL-PCG-009] Convoy %(name)s has no "
                    "vehicles."
                ) % {"name": convoy.name})
            convoy.state = "in_transit"
            convoy.actual_departure = fields.Datetime.now()

    def action_mark_arrived(self):
        for convoy in self:
            convoy.state = "arrived"
            convoy.actual_arrival = fields.Datetime.now()

    def action_cancel(self):
        for convoy in self:
            convoy.state = "cancelled"


class EhLogProjectCargoConvoyVehicle(models.Model):
    _name = "eh.log.project.cargo.convoy.vehicle"
    _description = "Convoy Vehicle Assignment"
    _order = "convoy_id, sequence, id"

    convoy_id = fields.Many2one(
        "eh.log.project.cargo.convoy",
        string="Convoy",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    equipment_id = fields.Many2one(
        "eh.log.project.cargo.equipment",
        string="Equipment",
        required=True,
        ondelete="restrict",
    )
    role = fields.Selection(
        [
            ("primary", "Primary Hauler"),
            ("secondary", "Secondary Hauler"),
            ("crane", "Lifting Crane"),
            ("escort_lead", "Lead Escort"),
            ("escort_trail", "Trailing Escort"),
            ("support", "Support"),
        ],
        string="Role",
        required=True,
        default="primary",
    )
    driver_partner_id = fields.Many2one("res.partner", string="Driver")
    notes = fields.Char(string="Notes")
    company_id = fields.Many2one(
        related="convoy_id.company_id",
        store=True,
        index=True,
    )

    @api.constrains("equipment_id")
    def _check_equipment_inspection(self):
        today = fields.Date.context_today(self)
        for vehicle in self:
            equipment = vehicle.equipment_id
            if (equipment.next_inspection_date
                    and equipment.next_inspection_date < today):
                raise ValidationError(_(
                    "[EHL-PCG-010] Equipment %(code)s is overdue "
                    "for statutory inspection (was %(date)s); it "
                    "cannot be assigned to a convoy until the "
                    "inspection date is updated."
                ) % {
                    "code": equipment.code,
                    "date": equipment.next_inspection_date,
                })
