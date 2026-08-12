# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order extension: last-mile flag and counter."""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_last_mile_required = fields.Boolean(
        string="Last Mile",
        default=False,
        tracking=True,
        help="When checked, the order is eligible for inclusion in a "
             "last-mile wave. The dispatcher creates the delivery "
             "record and assigns to a wave.",
    )

    eh_log_last_mile_delivery_ids = fields.One2many(
        "eh.log.last.mile.delivery",
        "sale_order_id",
        string="Last Mile Deliveries",
        copy=False,
        readonly=True,
    )

    eh_log_last_mile_delivery_count = fields.Integer(
        string="Last Mile Deliveries",
        compute="_compute_eh_log_last_mile_delivery_count",
    )

    @api.depends("eh_log_last_mile_delivery_ids")
    def _compute_eh_log_last_mile_delivery_count(self):
        for order in self:
            order.eh_log_last_mile_delivery_count = len(
                order.eh_log_last_mile_delivery_ids
            )

    def action_view_eh_log_last_mile_deliveries(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Last Mile Deliveries",
            "res_model": "eh.log.last.mile.delivery",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {"default_sale_order_id": self.id},
        }
