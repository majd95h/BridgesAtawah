# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order extension: surface declarations spawned from this order.

This module does not auto-spawn declarations on confirm because the
declaration depends on a regulator profile choice that the operator
makes after seeing the lane. The Create Customs Declaration button on
the spawned freight job is the supported path; this extension just
provides the smart-button counter on the order form.
"""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_customs_declaration_ids = fields.One2many(
        "eh.log.customs.declaration",
        "sale_order_id",
        string="Customs Declarations",
        copy=False,
        readonly=True,
    )

    eh_log_customs_declaration_count = fields.Integer(
        string="Customs Declarations",
        compute="_compute_eh_log_customs_declaration_count",
    )

    @api.depends("eh_log_customs_declaration_ids")
    def _compute_eh_log_customs_declaration_count(self):
        for order in self:
            order.eh_log_customs_declaration_count = len(
                order.eh_log_customs_declaration_ids
            )

    def action_view_eh_log_customs_declarations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Customs Declarations",
            "res_model": "eh.log.customs.declaration",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {"default_sale_order_id": self.id},
        }
