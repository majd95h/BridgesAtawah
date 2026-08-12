# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Route survey results.

A route survey is the engineer's reconnaissance of one route option:
walked or driven, every bridge measured, every overhead clearance
recorded, every weight-bearing constraint noted. Several surveys may
exist per job (different routes considered); the convoy points at
the survey it actually follows.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EhLogProjectCargoRouteSurvey(models.Model):
    _name = "eh.log.project.cargo.route.survey"
    _description = "Project Cargo Route Survey"
    _order = "job_id, sequence, id"
    _rec_names_search = ["name"]

    name = fields.Char(string="Route Name", required=True)
    sequence = fields.Integer(default=10)
    job_id = fields.Many2one(
        "eh.log.project.cargo.job",
        string="Job",
        required=True,
        ondelete="cascade",
        index=True,
    )
    surveyor_partner_id = fields.Many2one(
        "res.partner",
        string="Surveyor",
    )
    surveyed_at = fields.Date(
        string="Surveyed On",
        default=fields.Date.context_today,
    )
    distance_km = fields.Float(string="Distance (km)")
    estimated_duration_h = fields.Float(string="Estimated Duration (h)")
    min_overhead_clearance_m = fields.Float(
        string="Min Overhead Clearance (m)",
        help=(
            "Lowest overhead clearance encountered on the route. "
            "Driving constraint for tall cargo; the lift study "
            "checks against the cargo's transport height plus the "
            "trailer deck height."
        ),
    )
    min_swing_radius_m = fields.Float(
        string="Min Swing Radius (m)",
        help=(
            "Tightest swing radius encountered. Drives the choice "
            "of trailer (modular vs lowbed) and limits articulation."
        ),
    )
    max_axle_load_t = fields.Float(
        string="Max Bridge Axle Load (t)",
        help=(
            "Lowest bridge axle-load rating encountered. Constrains "
            "the convoy weight per axle line."
        ),
    )
    night_only = fields.Boolean(
        string="Night Move Only",
        default=False,
        help=(
            "Set when the route is restricted to night hours by the "
            "road authority. Drives permit selection and convoy "
            "scheduling."
        ),
    )
    hazards = fields.Text(
        string="Hazards",
        help="Free-text description of hazards encountered.",
    )
    waypoints = fields.Text(string="Waypoints / Notes")
    is_chosen_route = fields.Boolean(
        string="Chosen Route",
        default=False,
        help=(
            "Tick to mark this survey as the route the convoy will "
            "follow. Only one survey per job may be the chosen "
            "route."
        ),
    )
    company_id = fields.Many2one(
        related="job_id.company_id",
        store=True,
        index=True,
    )

    @api.constrains("is_chosen_route")
    def _check_one_chosen_route(self):
        for survey in self:
            if not survey.is_chosen_route:
                continue
            duplicates = self.search([
                ("job_id", "=", survey.job_id.id),
                ("is_chosen_route", "=", True),
                ("id", "!=", survey.id),
            ])
            if duplicates:
                raise ValidationError(_(
                    "[EHL-PCG-013] Job %(name)s already has a "
                    "chosen route survey; untick it first."
                ) % {"name": survey.job_id.name})
