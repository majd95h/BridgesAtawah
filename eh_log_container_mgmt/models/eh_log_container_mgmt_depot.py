# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Container depot master.

Depot identity, operator, capacity, gate hours. Reused across every
container record and every gate movement. Country localisation packs
ship country-specific depots as data records (e.g. UAE: DP World
ICAD-1, Khalifa Port, etc.; KSA: Mawani Jeddah ICD).
"""
from odoo import _, api, fields, models


class EhLogContainerMgmtDepot(models.Model):
    _name = "eh.log.container.mgmt.depot"
    _description = "Container Depot or Yard"
    _order = "code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(
        string="Code",
        required=True,
        index=True,
        help="Stable depot identifier (e.g. JEA-DP, KH-CMA, RAS-MMI).",
    )

    name = fields.Char(string="Name", required=True, translate=True)

    depot_kind = fields.Selection(
        selection=[
            ("port_terminal", "Port Container Terminal"),
            ("inland_depot", "Inland Container Depot"),
            ("dry_port", "Dry Port"),
            ("freezone_depot", "Free Zone Depot"),
            ("repair_yard", "Repair Yard"),
            ("storage_yard", "Storage Yard"),
        ],
        string="Depot Kind",
        required=True,
        default="storage_yard",
        index=True,
    )

    operator_id = fields.Many2one(
        "res.partner",
        string="Operator",
        index=True,
        help="The party operating the depot. Counterparty for "
             "movement and lift/handle billing.",
    )

    country_id = fields.Many2one("res.country", string="Country", index=True)

    address = fields.Text(string="Address")

    capacity_teu = fields.Integer(
        string="Capacity (TEU)",
        help="Indicative TEU capacity. Used by yard planning to "
             "raise warnings when occupancy approaches the limit.",
    )

    accepts_reefer = fields.Boolean(string="Accepts Reefer")
    accepts_dangerous = fields.Boolean(string="Accepts Dangerous Goods")
    accepts_tank = fields.Boolean(string="Accepts Tank")

    gate_hours = fields.Char(
        string="Gate Hours",
        help="Free-text description of gate operating hours, e.g. "
             "'24/7' or 'Sat-Thu 06:00-22:00'. The dispatch board "
             "warns when scheduled movements fall outside these hours.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_container_mgmt_depot_company_rel",
        "depot_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    notes = fields.Text(string="Notes")

    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        'UNIQUE(code)',
        'Depot code must be unique.',
    )

    @api.depends("company_id")
    def _compute_company_ids(self):
        for record in self:
            record.company_ids = record.company_id

    @api.depends("code", "name", "country_id")
    def _compute_display_name(self):
        for record in self:
            label = record.name
            if record.country_id:
                label = f"{label} ({record.country_id.code})"
            record.display_name = (
                f"[{record.code}] {label}" if record.code else label
            )
