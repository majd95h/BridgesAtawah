# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order extension: cold chain requirement and default profile."""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_cold_chain_required = fields.Boolean(
        string="Cold Chain Required",
        default=False,
        tracking=True,
        help="When checked, the freight job spawned from this order "
             "auto-creates a cold chain monitoring run.",
    )

    eh_log_cold_chain_profile_id = fields.Many2one(
        "eh.log.cold.chain.profile",
        string="Cold Chain Profile",
        tracking=True,
        help="Default profile applied to the spawned monitoring run. "
             "The operator can change it on the run before activation.",
    )
