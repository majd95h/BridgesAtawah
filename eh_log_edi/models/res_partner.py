# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Res partner extension: link to EDI configurations."""
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    eh_log_edi_partner_ids = fields.One2many(
        "eh.log.edi.partner",
        "partner_id",
        string="EDI Configurations",
    )
