# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""3PL rate card.

A rate card carries one row per chargeable service. The billing run
walks the movement log and the snapshot history, finds matching rate
lines, and emits billing lines.

Service types are a closed enum so the billing engine can dispatch
on a known set. Adding a new service requires extending the engine,
not just adding configuration data; this is intentional, the
business rules per service differ enough that a generic config-only
mechanism would hide bugs.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Service types the billing engine knows about. Each matches a code
# branch in eh_log_warehouse_billing_run._compute_charges.
SERVICE_TYPES = [
    ("storage_pallet_day", "Storage per Pallet per Day"),
    ("handling_in", "Handling In (per pallet)"),
    ("handling_out", "Handling Out (per pallet)"),
    ("pick_line", "Pick Line"),
    ("vas_kit", "Value-Added Services - Kit"),
    ("vas_label", "Value-Added Services - Label"),
    ("vas_scan", "Value-Added Services - Scan"),
    ("monthly_minimum", "Monthly Minimum Charge"),
]


class EhLogWarehouseRateCard(models.Model):
    _name = "eh.log.warehouse.rate.card"
    _description = "3PL Rate Card"
    _order = "name"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True, size=12)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "eh.log.warehouse.rate.line",
        "rate_card_id",
        string="Lines",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _rate_card_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Rate card code must be unique per company.',
    )

    def find_rate(self, service_type, product=None):
        """Return the line matching the requested service.

        If product is provided, prefer a line constrained to that
        product; fall back to a product-agnostic line. Returns False
        if neither match. The billing engine raises a configuration
        error in that case rather than silently dropping the charge.
        """
        self.ensure_one()
        product_match = self.line_ids.filtered(
            lambda l: l.service_type == service_type
            and product
            and l.product_id == product
        )
        if product_match:
            return product_match[:1]
        agnostic = self.line_ids.filtered(
            lambda l: l.service_type == service_type and not l.product_id
        )
        return agnostic[:1] if agnostic else False


class EhLogWarehouseRateLine(models.Model):
    _name = "eh.log.warehouse.rate.line"
    _description = "3PL Rate Line"
    _order = "rate_card_id, service_type"

    rate_card_id = fields.Many2one(
        "eh.log.warehouse.rate.card",
        string="Rate Card",
        required=True,
        ondelete="cascade",
    )
    service_type = fields.Selection(
        SERVICE_TYPES,
        string="Service",
        required=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product Override",
        help=(
            "Optional. Constrain this line to a specific product. "
            "If empty, the line applies to any product. The billing "
            "engine prefers product-specific lines."
        ),
    )
    unit_price = fields.Monetary(
        string="Unit Price",
        required=True,
        currency_field="currency_id",
    )
    minimum_quantity = fields.Float(
        string="Minimum Units",
        default=0.0,
        help=(
            "Minimum billable quantity for the period. If actual "
            "consumption is lower, the engine bills the minimum."
        ),
    )
    currency_id = fields.Many2one(
        related="rate_card_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="rate_card_id.company_id",
        store=True,
        index=True,
    )

    _rate_line_unique = models.Constraint(
        'unique(rate_card_id, service_type, product_id)',
        'Duplicate rate line for the same service and product.',
    )

    @api.constrains("unit_price")
    def _check_price_positive(self):
        for line in self:
            if line.unit_price < 0:
                raise ValidationError(_(
                    "[EHL-WHS-006] Rate line unit price cannot be "
                    "negative."
                ))
