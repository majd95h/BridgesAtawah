# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order link to disbursement account."""
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_ship_disbursement_account_id = fields.Many2one(
        "eh.log.ship.disbursement.account",
        string="Ship Disbursement Account",
        readonly=True,
        copy=False,
    )
