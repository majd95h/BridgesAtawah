# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Sale order link to project cargo job."""
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    eh_log_project_cargo_job_ids = fields.One2many(
        "eh.log.project.cargo.job",
        "sale_order_id",
        string="Project Cargo Jobs",
    )
