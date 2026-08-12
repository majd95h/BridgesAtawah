# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Rate-shop wizard.

Operator-facing form that collects the routing parameters, fans out
across the configured carriers, and surfaces the ranked quote list.
The wizard creates an eh.log.carrier.rate.request behind the scenes
so the audit trail remains complete even when the operator abandons
the wizard partway.

The wizard supports two outcomes:

* Continue: store the request and the quotes, move the operator to
  the request form to choose a quote.
* Auto-book: when only a single quote returns and it falls below the
  configured auto-book threshold, immediately spawn an
  eh.log.carrier.booking and surface that record.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EhLogCarrierRateShopWizard(models.TransientModel):
    _name = "eh.log.carrier.rate.shop.wizard"
    _description = "Rate Shop Wizard"

    mode = fields.Selection(
        [
            ("ocean", "Ocean"),
            ("air", "Air"),
            ("road", "Road"),
            ("rail", "Rail"),
        ],
        string="Mode",
        required=True,
        default="ocean",
    )
    origin_country_id = fields.Many2one(
        "res.country",
        string="Origin Country",
        required=True,
    )
    origin_location_code = fields.Char(string="Origin Location Code")
    destination_country_id = fields.Many2one(
        "res.country",
        string="Destination Country",
        required=True,
    )
    destination_location_code = fields.Char(string="Destination Location Code")
    ready_by_date = fields.Date(
        string="Ready By",
        required=True,
        default=fields.Date.context_today,
    )
    weight_kg = fields.Float(string="Weight (kg)")
    volume_cbm = fields.Float(string="Volume (CBM)")
    package_count = fields.Integer(string="Packages", default=1)
    is_dangerous_goods = fields.Boolean(string="Dangerous Goods")
    rank_strategy = fields.Selection(
        [
            ("cheapest", "Cheapest"),
            ("fastest", "Fastest Transit"),
            ("balanced", "Balanced"),
            ("preferred", "Preferred Carrier"),
        ],
        string="Rank Strategy",
        default="cheapest",
        required=True,
    )
    carrier_profile_ids = fields.Many2many(
        "eh.log.carrier.profile",
        string="Carriers",
        help=(
            "Optional. Constrain the fan-out to these carriers. If "
            "empty, every active carrier matching the mode is "
            "consulted."
        ),
    )
    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
    )

    def action_shop(self):
        self.ensure_one()
        if self.origin_country_id == self.destination_country_id and not (
            self.origin_location_code and self.destination_location_code
        ):
            raise UserError(_(
                "[EHL-CAR-011] Origin and destination countries are "
                "identical; supply distinct location codes for an "
                "intra-country shop."
            ))
        Request = self.env["eh.log.carrier.rate.request"]
        request = Request.create({
            "mode": self.mode,
            "origin_country_id": self.origin_country_id.id,
            "origin_location_code": self.origin_location_code or "",
            "destination_country_id": self.destination_country_id.id,
            "destination_location_code": self.destination_location_code or "",
            "ready_by_date": self.ready_by_date,
            "weight_kg": self.weight_kg,
            "volume_cbm": self.volume_cbm,
            "package_count": self.package_count,
            "is_dangerous_goods": self.is_dangerous_goods,
            "rank_strategy": self.rank_strategy,
            "freight_job_id": self.freight_job_id.id or False,
            "sale_order_id": self.sale_order_id.id or False,
            "company_id": self.env.company.id,
        })
        request.shop(self.carrier_profile_ids or None)
        return {
            "type": "ir.actions.act_window",
            "name": _("Rate Request"),
            "res_model": "eh.log.carrier.rate.request",
            "view_mode": "form",
            "res_id": request.id,
            "target": "current",
        }
