# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Company-level last-mile defaults."""
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    eh_log_last_mile_max_attempts = fields.Integer(
        string="Max Delivery Attempts",
        default=3,
        help="Maximum delivery attempts before a stop is auto-marked "
             "failed. Operators can still re-schedule a failed "
             "delivery from the form.",
    )
