# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Vessel master.

A vessel is identified by IMO (International Maritime Organization)
number, the durable global identifier that survives ownership and
name changes. The IMO is seven digits with a checksum; the validator
enforces the checksum so a typo cannot create an unrecoverable
record.

Owner and operator are usually different partners (the registered
owner is often a single-purpose vehicle; the operator is the actual
shipping line). Both are captured so the agent has the right billing
party available without manual lookup.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Vessel type enumeration. Closed list because each downstream form
# (port call, husbandry catalog) drives behaviour by the type. Adding
# a new type requires extending the form filters too.
VESSEL_TYPES = [
    ("container", "Container"),
    ("bulk", "Bulk Carrier"),
    ("tanker", "Tanker"),
    ("general", "General Cargo"),
    ("ro_ro", "Ro-Ro"),
    ("reefer", "Reefer"),
    ("cruise", "Cruise"),
    ("other", "Other"),
]


def _validate_imo(value: str) -> bool:
    """Validate IMO checksum per IMO Resolution A.1078(28).

    The checksum digit is the last digit; the leading six digits are
    multiplied by weights 7, 6, 5, 4, 3, 2 and summed; the result
    modulo 10 must equal the checksum. Returns True on valid input.
    """
    if not value:
        return False
    cleaned = value.replace("IMO", "").replace(" ", "").strip()
    if len(cleaned) != 7 or not cleaned.isdigit():
        return False
    weights = (7, 6, 5, 4, 3, 2)
    total = sum(int(cleaned[i]) * weights[i] for i in range(6))
    return total % 10 == int(cleaned[6])


class EhLogShipVessel(models.Model):
    _name = "eh.log.ship.vessel"
    _description = "Vessel"
    _order = "name"
    _rec_names_search = ["name", "imo_number", "call_sign"]
    _inherit = ["mail.thread"]

    name = fields.Char(string="Name", required=True, tracking=True)
    imo_number = fields.Char(
        string="IMO Number",
        required=True,
        size=10,
        tracking=True,
        help=(
            "Seven-digit IMO number. Stable global identifier; "
            "survives name and ownership changes. The checksum is "
            "validated at save time."
        ),
    )
    call_sign = fields.Char(string="Call Sign", size=10, tracking=True)
    mmsi = fields.Char(
        string="MMSI",
        size=9,
        tracking=True,
        help="Maritime Mobile Service Identity (9 digits).",
    )
    flag_country_id = fields.Many2one(
        "res.country",
        string="Flag",
        tracking=True,
    )
    vessel_type = fields.Selection(
        VESSEL_TYPES,
        string="Type",
        required=True,
        default="container",
        tracking=True,
    )
    gross_tonnage = fields.Float(
        string="Gross Tonnage (GT)",
        help="Volumetric measurement of internal capacity.",
    )
    net_tonnage = fields.Float(string="Net Tonnage (NT)")
    deadweight_tonnage = fields.Float(string="Deadweight (DWT)")
    length_overall_m = fields.Float(string="LOA (m)")
    beam_m = fields.Float(string="Beam (m)")
    draft_m = fields.Float(string="Draft (m)")
    owner_partner_id = fields.Many2one(
        "res.partner",
        string="Registered Owner",
        tracking=True,
    )
    operator_partner_id = fields.Many2one(
        "res.partner",
        string="Operator",
        tracking=True,
        help=(
            "Commercial operator. Often distinct from the registered "
            "owner; this is the partner the agent invoices."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True, tracking=True)

    _imo_unique = models.Constraint(
        'unique(imo_number, company_id)',
        'IMO number must be unique per company.',
    )

    @api.constrains("imo_number")
    def _check_imo_format(self):
        for vessel in self:
            if not _validate_imo(vessel.imo_number):
                raise ValidationError(_(
                    "[EHL-SHP-001] IMO number %(imo)s is invalid. "
                    "Must be exactly seven digits with a valid IMO "
                    "checksum (Resolution A.1078(28))."
                ) % {"imo": vessel.imo_number})

    @api.constrains("mmsi")
    def _check_mmsi_format(self):
        for vessel in self:
            if not vessel.mmsi:
                continue
            cleaned = vessel.mmsi.strip()
            if len(cleaned) != 9 or not cleaned.isdigit():
                raise ValidationError(_(
                    "[EHL-SHP-002] MMSI %(mmsi)s must be exactly "
                    "nine digits."
                ) % {"mmsi": vessel.mmsi})
