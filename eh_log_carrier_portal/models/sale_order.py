# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order link to carrier rate request."""
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_carrier_rate_request_ids = fields.One2many(
        "eh.log.carrier.rate.request",
        "sale_order_id",
        string="Carrier Rate Requests",
    )
