# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Settings page bindings for track-and-trace.

Two operator-facing values: the public base URL (which hostname
appears in tracking links) and the token salt (rotating it
invalidates outstanding links). Stored as ir.config_parameter rows
so the trackable mixin can read them without needing the company
record.
"""
from odoo import fields, models


PUBLIC_BASE_URL_PARAM = "eh_log_track_trace.public_base_url"
TOKEN_SALT_PARAM = "eh_log_track_trace.token_salt"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    eh_log_track_public_base_url = fields.Char(
        string="Tracking Public Base URL",
        config_parameter=PUBLIC_BASE_URL_PARAM,
        help=(
            "Hostname customers see in tracking URLs. Falls back to "
            "the system base URL if blank."
        ),
    )
    eh_log_track_token_salt = fields.Char(
        string="Tracking Token Salt",
        config_parameter=TOKEN_SALT_PARAM,
        help=(
            "Per-database salt used to derive non-enumerable public "
            "tracking tokens. Rotate to invalidate outstanding "
            "tracking links."
        ),
    )
