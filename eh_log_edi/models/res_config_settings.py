# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""EDI hub settings."""
from odoo import fields, models


PARAM_SELF_IDENTIFIER = "eh_log_edi.self_identifier"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    eh_log_edi_self_identifier = fields.Char(
        string="EDI Self Identifier",
        config_parameter=PARAM_SELF_IDENTIFIER,
        help=(
            "Identifier (GLN, DUNS, internal) inserted as the sender "
            "party on every outbound EDI envelope. Per-partner "
            "configurations may override this value."
        ),
    )
