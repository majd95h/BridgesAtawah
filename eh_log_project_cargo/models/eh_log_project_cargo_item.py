# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Per-piece cargo item with dimensional and engineering data.

Each row captures one oversized / heavy piece. The dimensional
envelope check fires at save time and at every dimension change: any
length, width, height, or weight that exceeds the configured
standard envelope sets is_oversized to True. Downstream planning
(convoy assembly, permit register) reads is_oversized to decide
whether escort vehicles and route surveys are required.

Engineering fields (centre of gravity, lift point coordinates) are
free-text; encoding them as structured fields would imply more
precision than the engineering studies usually carry at the
forwarder's stage. The lift contractor refines them in their own
calc package.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Standard road / sea envelope thresholds. Anything exceeding any of
# these flags as oversized. Operators may tighten these per-company
# in a future ir.config_parameter override; the constants give a
# universally accepted floor (rough averages from European, GCC, and
# US road regulations).
STANDARD_LENGTH_M = 16.5
STANDARD_WIDTH_M = 2.55
STANDARD_HEIGHT_M = 4.0
STANDARD_WEIGHT_T = 44.0


class EhLogProjectCargoItem(models.Model):
    _name = "eh.log.project.cargo.item"
    _description = "Project Cargo Item"
    _order = "job_id, sequence, id"

    job_id = fields.Many2one(
        "eh.log.project.cargo.job",
        string="Job",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description", required=True)
    quantity = fields.Integer(string="Quantity", default=1)
    length_m = fields.Float(string="Length (m)")
    width_m = fields.Float(string="Width (m)")
    height_m = fields.Float(string="Height (m)")
    weight_t = fields.Float(string="Weight per Piece (t)")
    cog_x_m = fields.Float(
        string="COG Offset X (m)",
        help="Centre of gravity offset along length axis from the geometric centre.",
    )
    cog_y_m = fields.Float(string="COG Offset Y (m)")
    cog_z_m = fields.Float(string="COG Offset Z (m)")
    lift_points_notes = fields.Text(
        string="Lift Points",
        help=(
            "Free-text description of designated lift points or "
            "cradle / saddle requirements. The lift contractor's "
            "calc package consumes the canonical structured form; "
            "this is the forwarder's working note."
        ),
    )
    transport_orientation = fields.Selection(
        [
            ("upright", "Upright"),
            ("on_side", "On Side"),
            ("inverted", "Inverted"),
        ],
        string="Transport Orientation",
        default="upright",
    )
    packing_notes = fields.Text(string="Packing / Protection Notes")
    is_oversized = fields.Boolean(
        string="Oversized",
        compute="_compute_is_oversized",
        store=True,
        help=(
            "Auto-derived from dimensions vs the standard envelope. "
            "Drives downstream requirements (escort, permits, "
            "route survey)."
        ),
    )
    company_id = fields.Many2one(
        related="job_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("length_m", "width_m", "height_m", "weight_t")
    def _compute_is_oversized(self):
        for item in self:
            item.is_oversized = (
                (item.length_m or 0.0) > STANDARD_LENGTH_M
                or (item.width_m or 0.0) > STANDARD_WIDTH_M
                or (item.height_m or 0.0) > STANDARD_HEIGHT_M
                or (item.weight_t or 0.0) > STANDARD_WEIGHT_T
            )

    @api.constrains("length_m", "width_m", "height_m", "weight_t")
    def _check_dimensions_positive(self):
        for item in self:
            for label, value in (
                ("length", item.length_m),
                ("width", item.width_m),
                ("height", item.height_m),
                ("weight", item.weight_t),
            ):
                if value and value < 0:
                    raise ValidationError(_(
                        "[EHL-PCG-007] Item %(name)s %(label)s "
                        "cannot be negative."
                    ) % {"name": item.name, "label": label})
