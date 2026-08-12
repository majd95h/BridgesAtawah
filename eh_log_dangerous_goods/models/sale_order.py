# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order extension: dangerous-goods requirement and counter."""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_dg_required = fields.Boolean(
        string="Dangerous Goods",
        default=False,
        tracking=True,
        help="When checked, the freight job spawned from this order "
             "auto-creates a Dangerous Goods declaration.",
    )

    eh_log_dg_declaration_ids = fields.One2many(
        "eh.log.dg.declaration",
        "sale_order_id",
        string="DG Declarations",
        copy=False,
        readonly=True,
    )

    eh_log_dg_declaration_count = fields.Integer(
        string="DG Declarations",
        compute="_compute_eh_log_dg_declaration_count",
    )

    @api.depends("eh_log_dg_declaration_ids")
    def _compute_eh_log_dg_declaration_count(self):
        for order in self:
            order.eh_log_dg_declaration_count = len(order.eh_log_dg_declaration_ids)

    def action_view_eh_log_dg_declarations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "DG Declarations",
            "res_model": "eh.log.dg.declaration",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {"default_sale_order_id": self.id},
        }
