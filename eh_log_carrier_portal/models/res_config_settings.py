# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Settings for the carrier portal."""
from odoo import fields, models


PARAM_DEFAULT_RANK_STRATEGY = "eh_log_carrier_portal.default_rank_strategy"
PARAM_AUTO_BOOK_THRESHOLD = "eh_log_carrier_portal.auto_book_threshold"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    eh_log_carrier_default_rank_strategy = fields.Selection(
        [
            ("cheapest", "Cheapest"),
            ("fastest", "Fastest Transit"),
            ("balanced", "Balanced"),
            ("preferred", "Preferred Carrier"),
        ],
        string="Default Rank Strategy",
        config_parameter=PARAM_DEFAULT_RANK_STRATEGY,
        default="cheapest",
    )
    eh_log_carrier_auto_book_threshold = fields.Float(
        string="Auto-Book Threshold",
        config_parameter=PARAM_AUTO_BOOK_THRESHOLD,
        default=0.0,
        help=(
            "When a single quote comes in below this value, the "
            "rate-shop wizard auto-books it. Set to 0 to disable."
        ),
    )
