# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Heavy-lift equipment master.

A heavy-lift project consumes equipment in three rough categories:

* Lifting equipment: cranes (mobile, crawler, telescopic, rough-
  terrain), gantries, lifting frames.
* Transport equipment: prime movers, modular trailers, SPMTs
  (self-propelled modular transporters), ramps.
* Escort and support: pilot vehicles, BSO (banksman supervisor)
  vehicles, generator sets.

Each row carries the capability data planning needs: maximum lift
capacity at boom radius, axle load, modular configuration limits,
fuel envelope. The fields are intentionally general; specialised
fields (for SPMT axle line counts, etc.) are exposed conditionally
based on the equipment type.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Closed enum. Each branch in the form view shows / hides the
# specialised fields appropriate to the type. New types require
# extending the enum and the conditional view xpath together.
EQUIPMENT_TYPES = [
    ("crane_mobile", "Mobile Crane"),
    ("crane_crawler", "Crawler Crane"),
    ("crane_telescopic", "Telescopic Crane"),
    ("crane_gantry", "Gantry Crane"),
    ("prime_mover", "Prime Mover"),
    ("trailer_modular", "Modular Trailer"),
    ("trailer_lowbed", "Lowbed Trailer"),
    ("spmt", "SPMT (Self-Propelled Modular)"),
    ("escort", "Escort Vehicle"),
    ("ramp", "Ramp / Loadbed"),
    ("rigging", "Rigging Accessory"),
    ("other", "Other"),
]


class EhLogProjectCargoEquipment(models.Model):
    _name = "eh.log.project.cargo.equipment"
    _description = "Heavy-Lift Equipment"
    _order = "equipment_type, name"
    _rec_names_search = ["name", "code"]
    _inherit = ["mail.thread"]

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, size=12, tracking=True)
    equipment_type = fields.Selection(
        EQUIPMENT_TYPES,
        string="Type",
        required=True,
        default="crane_mobile",
        tracking=True,
    )
    owner_partner_id = fields.Many2one(
        "res.partner",
        string="Owner",
        help=(
            "Partner that owns the equipment. Internal fleet uses "
            "the company partner; rented kit references the rental "
            "company so cost reconciliation has the right vendor."
        ),
    )
    rated_capacity_t = fields.Float(
        string="Rated Capacity (t)",
        help=(
            "For cranes: lift capacity at the manufacturer's "
            "reference radius. For trailers: payload."
        ),
    )
    max_boom_radius_m = fields.Float(string="Max Boom Radius (m)")
    max_boom_length_m = fields.Float(string="Max Boom Length (m)")
    axle_count = fields.Integer(string="Axle Lines")
    spmt_axle_lines = fields.Integer(
        string="SPMT Axle Lines",
        help="Number of axle lines per SPMT module.",
    )
    spmt_modules_available = fields.Integer(
        string="SPMT Modules Available",
        help="How many modules can be coupled in this configuration.",
    )
    self_weight_t = fields.Float(string="Self Weight (t)")
    home_depot = fields.Char(string="Home Depot")
    next_inspection_date = fields.Date(
        string="Next Inspection",
        tracking=True,
        help=(
            "Statutory inspection due date. Equipment with a past "
            "due-date is blocked from new convoy assignments."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True, tracking=True)

    _equipment_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Equipment code must be unique per company.',
    )

    @api.constrains("rated_capacity_t")
    def _check_capacity_positive(self):
        for equipment in self:
            if equipment.rated_capacity_t and equipment.rated_capacity_t <= 0:
                raise ValidationError(_(
                    "[EHL-PCG-001] Equipment %(code)s rated capacity "
                    "must be positive."
                ) % {"code": equipment.code})

    def action_check_inspection(self):
        """Return list of equipment overdue for inspection."""
        today = fields.Date.context_today(self)
        return self.filtered(
            lambda e: e.next_inspection_date and e.next_inspection_date < today
        )
