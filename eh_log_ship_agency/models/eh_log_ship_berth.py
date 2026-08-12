# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Berth master.

A berth is one alongside position at a port. Carries the depth, the
maximum LOA the berth can accept, the terminal operator, the customs
status (bonded vs domestic). Used to sanity-check vessel assignment
on a port call: a vessel with draft greater than the berth depth or
LOA greater than the berth maximum is rejected.

The port itself is the standard res.partner record with the country
set; ports are not modelled separately to keep the schema thin.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EhLogShipBerth(models.Model):
    _name = "eh.log.ship.berth"
    _description = "Berth"
    _order = "port_partner_id, code"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True, size=12)
    port_partner_id = fields.Many2one(
        "res.partner",
        string="Port",
        required=True,
        ondelete="restrict",
        domain="[('is_company', '=', True)]",
        help=(
            "Port authority partner. Reused on port-call records and "
            "billing without needing a dedicated port master table."
        ),
    )
    depth_m = fields.Float(string="Depth (m)")
    max_loa_m = fields.Float(string="Max LOA (m)")
    terminal_operator_partner_id = fields.Many2one(
        "res.partner",
        string="Terminal Operator",
    )
    customs_status = fields.Selection(
        [
            ("bonded", "Bonded"),
            ("domestic", "Domestic"),
            ("free_zone", "Free Zone"),
        ],
        string="Customs Status",
        default="domestic",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _berth_code_unique = models.Constraint(
        'unique(port_partner_id, code, company_id)',
        'Berth code must be unique per port.',
    )

    @api.constrains("depth_m", "max_loa_m")
    def _check_positive_dimensions(self):
        for berth in self:
            if berth.depth_m and berth.depth_m <= 0:
                raise ValidationError(_(
                    "[EHL-SHP-003] Berth %(code)s depth must be "
                    "positive."
                ) % {"code": berth.code})
            if berth.max_loa_m and berth.max_loa_m <= 0:
                raise ValidationError(_(
                    "[EHL-SHP-004] Berth %(code)s max LOA must be "
                    "positive."
                ) % {"code": berth.code})

    def check_compatibility(self, vessel):
        """Return list of incompatibility messages (empty == OK)."""
        self.ensure_one()
        problems = []
        if self.depth_m and vessel.draft_m and vessel.draft_m > self.depth_m:
            problems.append(_(
                "Vessel draft %(draft)sm exceeds berth depth "
                "%(depth)sm."
            ) % {"draft": vessel.draft_m, "depth": self.depth_m})
        if self.max_loa_m and vessel.length_overall_m and vessel.length_overall_m > self.max_loa_m:
            problems.append(_(
                "Vessel LOA %(loa)sm exceeds berth max LOA "
                "%(max)sm."
            ) % {"loa": vessel.length_overall_m, "max": self.max_loa_m})
        return problems
