# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Customs declaration line: per-HS-code detail."""
from odoo import _, api, fields, models


class EhLogCustomsDeclarationLine(models.Model):
    _name = "eh.log.customs.declaration.line"
    _description = "Customs Declaration Line"
    _order = "declaration_id, sequence, id"
    _rec_name = "description"

    declaration_id = fields.Many2one(
        "eh.log.customs.declaration",
        string="Declaration",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sequence = fields.Integer(default=10)

    hs_code_id = fields.Many2one(
        "eh.log.customs.hs.code",
        string="HS Code",
        required=True,
        index=True,
    )

    description = fields.Char(
        string="Description",
        required=True,
    )

    country_of_origin_id = fields.Many2one(
        "res.country",
        string="Country of Origin",
        index=True,
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
    )

    unit_value = fields.Monetary(
        string="Unit Value",
        currency_field="currency_id",
    )

    customs_value = fields.Monetary(
        string="Customs Value",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    duty_rate_pct = fields.Float(
        string="Duty Rate (%)",
    )

    vat_rate_pct = fields.Float(
        string="VAT Rate (%)",
    )

    duty_amount = fields.Monetary(
        string="Duty",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    vat_amount = fields.Monetary(
        string="VAT",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    currency_id = fields.Many2one(
        related="declaration_id.currency_id",
        store=True,
        readonly=True,
    )

    notes = fields.Char()

    @api.onchange("hs_code_id")
    def _onchange_hs_code(self):
        if self.hs_code_id:
            if not self.duty_rate_pct:
                self.duty_rate_pct = self.hs_code_id.duty_rate_pct
            if not self.vat_rate_pct:
                self.vat_rate_pct = self.hs_code_id.vat_rate_pct
            if not self.description:
                self.description = self.hs_code_id.name

    @api.depends("quantity", "unit_value", "duty_rate_pct", "vat_rate_pct")
    def _compute_amounts(self):
        for line in self:
            value = (line.quantity or 0.0) * (line.unit_value or 0.0)
            line.customs_value = value
            duty = value * (line.duty_rate_pct or 0.0) / 100.0
            line.duty_amount = duty
            line.vat_amount = (value + duty) * (line.vat_rate_pct or 0.0) / 100.0
