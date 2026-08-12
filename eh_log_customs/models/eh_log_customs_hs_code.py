# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Harmonised System code reference.

Hierarchical: chapter (2 digits) -> heading (4 digits) -> subheading
(6 digits) -> national (8, 10 digits as country requires). The base
ships chapter-level seed only; country packs supply the deeper
national tariff overlays with country-specific duty and VAT rates.

Validation: code must be all-digit, length in (2, 4, 6, 8, 10).
"""
import re

from odoo import _, api, fields, models

from odoo.addons.eh_log_base.exceptions import EhLogValidationError


HS_CODE_RE = re.compile(r"^\d{2,10}$")
HS_VALID_LENGTHS = {2, 4, 6, 8, 10}


class EhLogCustomsHsCode(models.Model):
    _name = "eh.log.customs.hs.code"
    _description = "Harmonised System (HS) Code"
    _order = "code"
    _rec_names_search = ["code", "name"]
    _parent_store = True
    _parent_name = "parent_id"

    code = fields.Char(
        string="HS Code",
        required=True,
        index=True,
        help="Numeric. 2 digits = chapter, 4 = heading, 6 = WCO "
             "subheading, 8 or 10 = national tariff line.",
    )

    name = fields.Char(
        string="Description",
        required=True,
        translate=True,
    )

    level = fields.Selection(
        selection=[
            ("chapter", "Chapter (2 digits)"),
            ("heading", "Heading (4 digits)"),
            ("subheading", "Subheading (6 digits)"),
            ("national_8", "National (8 digits)"),
            ("national_10", "National (10 digits)"),
        ],
        string="Level",
        compute="_compute_level",
        store=True,
        index=True,
    )

    parent_id = fields.Many2one(
        "eh.log.customs.hs.code",
        string="Parent",
        ondelete="cascade",
        index=True,
    )

    parent_path = fields.Char(index=True)

    child_ids = fields.One2many(
        "eh.log.customs.hs.code",
        "parent_id",
        string="Children",
    )

    country_id = fields.Many2one(
        "res.country",
        string="Country",
        index=True,
        help="Empty for WCO-level codes (chapter, heading, subheading). "
             "Country pack national overlays carry the country.",
    )

    duty_rate_pct = fields.Float(
        string="Duty Rate (%)",
        help="Default ad valorem duty rate at this code. Can be "
             "overridden per declaration line.",
    )

    vat_rate_pct = fields.Float(
        string="VAT Rate (%)",
        help="Default destination VAT rate. Country packs set this "
             "per national overlay.",
    )

    notes = fields.Text(translate=True)

    active = fields.Boolean(default=True)

    _code_country_unique = models.Constraint(
        'UNIQUE(code, country_id)',
        'HS code must be unique per country (empty country = WCO scope).',
    )

    @api.depends("code")
    def _compute_level(self):
        level_map = {
            2: "chapter",
            4: "heading",
            6: "subheading",
            8: "national_8",
            10: "national_10",
        }
        for record in self:
            record.level = level_map.get(len(record.code or ""), False)

    @api.constrains("code")
    def _check_code_format(self):
        for record in self:
            if not HS_CODE_RE.match(record.code or ""):
                raise EhLogValidationError(
                    7,
                    _(
                        "HS code %(code)s is not numeric. HS codes are "
                        "all-digit, length 2 / 4 / 6 / 8 / 10."
                    ) % {"code": record.code},
                )
            if len(record.code) not in HS_VALID_LENGTHS:
                raise EhLogValidationError(
                    8,
                    _(
                        "HS code %(code)s has invalid length %(length)d. "
                        "Allowed lengths: 2 (chapter), 4 (heading), "
                        "6 (subheading), 8 or 10 (national)."
                    ) % {"code": record.code, "length": len(record.code)},
                )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"[{record.code}] {record.name}" if record.code else record.name
            )
