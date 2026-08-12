# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Settings UI extension for last-mile defaults."""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    eh_log_last_mile_max_attempts = fields.Integer(
        related="company_id.eh_log_last_mile_max_attempts",
        readonly=False,
    )

    eh_log_last_mile_max_attempts_param = fields.Integer(
        string="Last Mile Max Attempts (system param)",
        help="System-wide cap mirrored as ir.config_parameter "
             "eh_log_last_mile.max_attempts so the action methods "
             "read it without a per-company lookup on every call.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env["ir.config_parameter"].sudo()
        res["eh_log_last_mile_max_attempts_param"] = int(
            ICP.get_param("eh_log_last_mile.max_attempts", default="3")
        )
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param(
            "eh_log_last_mile.max_attempts",
            str(self.eh_log_last_mile_max_attempts_param or 3),
        )
