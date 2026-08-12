# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Carrier profile registry.

A profile is one carrier integration scoped to one company. The
profile points at an adapter (registered in eh_log_base.adapter_registry
under a PROVIDER_CODE) and carries the credentials key, the endpoint
URL, and the capability flags that drive the rate-shop and booking
flows.

Capability flags are intentionally explicit rather than inferred.
"This carrier supports rate_shop" must be set on the profile, not
guessed from the adapter class. That keeps a misconfigured profile
from crashing the rate-shop fan-out at the carrier-call boundary.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.eh_log_base import adapter_registry


class EhLogCarrierProfile(models.Model):
    _name = "eh.log.carrier.profile"
    _description = "Carrier Profile"
    _order = "mode, name"
    _rec_names_search = ["name", "code"]
    _inherit = ["mail.thread"]

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, size=12, tracking=True)
    mode = fields.Selection(
        [
            ("ocean", "Ocean"),
            ("air", "Air"),
            ("road", "Road"),
            ("rail", "Rail"),
            ("multi", "Multimodal"),
        ],
        string="Mode",
        required=True,
        tracking=True,
    )
    provider_code = fields.Char(
        string="Provider Code",
        required=True,
        tracking=True,
        help=(
            "Matches the PROVIDER_CODE class attribute on a "
            "registered carrier adapter. Validated at save time so "
            "a typo surfaces before a rate-shop fan-out."
        ),
    )
    api_version = fields.Char(string="API Version")
    endpoint_url = fields.Char(string="Endpoint URL")
    credentials_key = fields.Char(
        string="Credentials Key",
        required=True,
        help=(
            "Lookup key passed to the credentials helper. The actual "
            "secret never leaves the credentials store."
        ),
    )
    timeout_seconds = fields.Integer(
        string="Timeout (s)",
        default=30,
        help=(
            "Per-call timeout. Rate-shop fan-out runs all carriers "
            "in parallel up to this timeout; a slow carrier is "
            "skipped from the ranking."
        ),
    )
    can_rate_shop = fields.Boolean(string="Rate Shop", default=True)
    can_book = fields.Boolean(string="Book", default=True)
    can_cancel = fields.Boolean(string="Cancel", default=True)
    can_track = fields.Boolean(string="Track Status", default=True)
    can_schedules = fields.Boolean(string="Schedules", default=False)
    is_mock = fields.Boolean(
        string="Mock Provider",
        default=False,
        help=(
            "Mock providers always return canned data. Useful for "
            "tests and demos; never assign a mock profile to a real "
            "freight job."
        ),
    )
    is_preferred = fields.Boolean(
        string="Preferred",
        default=False,
        help=(
            "Bumps this carrier to the top under the 'preferred' "
            "rank strategy. Tie-broken by price."
        ),
    )
    eh_log_carrier_lane_ids = fields.One2many(
        "eh.log.carrier.lane",
        "carrier_profile_id",
        string="Lanes",
    )
    lane_count = fields.Integer(
        string="Lanes",
        compute="_compute_lane_count",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True, tracking=True)

    _carrier_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Carrier code must be unique per company.',
    )

    @api.depends("eh_log_carrier_lane_ids")
    def _compute_lane_count(self):
        for profile in self:
            profile.lane_count = len(profile.eh_log_carrier_lane_ids)

    @api.constrains("provider_code")
    def _check_provider_registered(self):
        for profile in self:
            if not profile.provider_code:
                continue
            adapter_cls = adapter_registry.get(profile.provider_code)
            if not adapter_cls:
                raise ValidationError(_(
                    "[EHL-CAR-001] Provider code %(code)s is not "
                    "registered. Install or activate the module that "
                    "provides this adapter."
                ) % {"code": profile.provider_code})

    def get_adapter(self):
        """Resolve and instantiate the adapter for this profile."""
        self.ensure_one()
        adapter_cls = adapter_registry.get(self.provider_code)
        if not adapter_cls:
            raise UserError(_(
                "[EHL-CAR-002] No adapter registered for provider "
                "code %(code)s."
            ) % {"code": self.provider_code})
        return adapter_cls(self.env, self)

    def action_health_check(self):
        """Ping the carrier and surface the result on the form."""
        self.ensure_one()
        adapter = self.get_adapter()
        result = adapter.health_check()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Health Check"),
                "message": _("OK") if result.ok else _("Failed"),
                "type": "success" if result.ok else "danger",
                "sticky": False,
            },
        }
