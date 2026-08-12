# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Settings for disputes and variations."""
from odoo import fields, models


PARAM_VARIATION_APPROVAL_LIMIT = "eh_log_disputes_variations.variation_approval_limit"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    eh_log_variation_approval_limit = fields.Float(
        string="Variation Approval Limit",
        config_parameter=PARAM_VARIATION_APPROVAL_LIMIT,
        default=0.0,
        help=(
            "Net amount above which variation approval requires the "
            "manager group. Below the limit, the user group can "
            "approve. Set to 0 to require manager approval for all "
            "variations."
        ),
    )
