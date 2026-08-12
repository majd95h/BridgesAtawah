# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Persisted rate-shop request and quotes.

A rate request captures the route + cargo + ready-by parameters and
the list of carriers consulted. Each carrier reply lands as a quote
row keyed back to the request.

Both the request and the quotes are immutable once stored. Re-quoting
the same parameters creates a new request rather than overwriting,
so historic decisions remain auditable.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Currency-agnostic ranking strategies. The wizard reads the user's
# choice and orders the quote list before presenting.
RANK_STRATEGIES = [
    ("cheapest", "Cheapest"),
    ("fastest", "Fastest Transit"),
    ("balanced", "Balanced (Price + Transit)"),
    ("preferred", "Preferred Carrier"),
]


class EhLogCarrierRateRequest(models.Model):
    _name = "eh.log.carrier.rate.request"
    _description = "Carrier Rate Request"
    _order = "create_date desc, id desc"
    _rec_names_search = ["name"]
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("shopped", "Shopped"),
            ("expired", "Expired"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    mode = fields.Selection(
        [
            ("ocean", "Ocean"),
            ("air", "Air"),
            ("road", "Road"),
            ("rail", "Rail"),
        ],
        string="Mode",
        required=True,
        tracking=True,
    )
    origin_country_id = fields.Many2one(
        "res.country",
        string="Origin Country",
        required=True,
    )
    origin_location_code = fields.Char(string="Origin Location Code")
    destination_country_id = fields.Many2one(
        "res.country",
        string="Destination Country",
        required=True,
    )
    destination_location_code = fields.Char(string="Destination Location Code")
    ready_by_date = fields.Date(
        string="Ready By",
        required=True,
        default=fields.Date.context_today,
    )
    weight_kg = fields.Float(string="Weight (kg)", default=0.0)
    volume_cbm = fields.Float(string="Volume (CBM)", default=0.0)
    package_count = fields.Integer(string="Packages", default=1)
    is_dangerous_goods = fields.Boolean(string="Dangerous Goods", default=False)
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="set null",
    )
    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
        ondelete="set null",
    )
    quote_ids = fields.One2many(
        "eh.log.carrier.rate.quote",
        "request_id",
        string="Quotes",
    )
    quote_count = fields.Integer(
        string="Quotes",
        compute="_compute_quote_count",
        store=True,
    )
    rank_strategy = fields.Selection(
        RANK_STRATEGIES,
        string="Rank Strategy",
        default="cheapest",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.carrier.rate.request"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("quote_ids")
    def _compute_quote_count(self):
        for request in self:
            request.quote_count = len(request.quote_ids)

    # ------------------------------------------------------------------
    # Fan-out
    # ------------------------------------------------------------------
    def shop(self, carrier_profiles=None):
        """Fan out the rate request across the carrier profiles.

        If carrier_profiles is None, every active profile in the
        same company that supports rate_shop and matches the mode
        is consulted. The lane filter further narrows the set.
        """
        self.ensure_one()
        Profile = self.env["eh.log.carrier.profile"]
        if carrier_profiles is None:
            carrier_profiles = Profile.search([
                ("active", "=", True),
                ("can_rate_shop", "=", True),
                ("mode", "in", (self.mode, "multi")),
                ("company_id", "=", self.company_id.id),
            ])
        for profile in carrier_profiles:
            if profile.eh_log_carrier_lane_ids:
                matching = profile.eh_log_carrier_lane_ids.filtered(
                    lambda l: l.matches(
                        self.origin_country_id.code,
                        self.destination_country_id.code,
                        self.origin_location_code,
                        self.destination_location_code,
                    )
                )
                if not matching:
                    _logger.info(
                        "Rate-shop %s: carrier %s skipped (no matching lane).",
                        self.name, profile.code,
                    )
                    continue
            self._call_carrier(profile)
        self.with_context(eh_log_carrier_internal_state_write=True).write({
            "state": "shopped",
        })
        return True

    def _call_carrier(self, profile):
        self.ensure_one()
        adapter = profile.get_adapter()
        payload = self._build_rate_shop_payload()
        result = adapter.call("rate_shop", payload, related_model=self._name)
        if not result.ok:
            _logger.info(
                "Rate-shop %s carrier %s call failed: %s",
                self.name, profile.code, result.error,
            )
            return False
        parsed = result.parsed or {}
        for offer in parsed.get("offers", []):
            self.env["eh.log.carrier.rate.quote"].with_context(
                eh_log_carrier_internal_quote_create=True,
            ).create({
                "request_id": self.id,
                "carrier_profile_id": profile.id,
                "service_name": offer.get("service_name", ""),
                "transit_days": offer.get("transit_days", 0),
                "price": offer.get("price", 0.0),
                "currency_id": self._resolve_currency(
                    offer.get("currency_code")
                ).id,
                "valid_until": offer.get("valid_until"),
                "carrier_quote_reference": offer.get("reference", ""),
                "raw_response": result.raw_response or "",
                "company_id": self.company_id.id,
            })
        return True

    def _build_rate_shop_payload(self):
        self.ensure_one()
        return {
            "request_reference": self.name,
            "mode": self.mode,
            "origin": {
                "country_code": self.origin_country_id.code,
                "location_code": self.origin_location_code or "",
            },
            "destination": {
                "country_code": self.destination_country_id.code,
                "location_code": self.destination_location_code or "",
            },
            "ready_by": self.ready_by_date.isoformat(),
            "cargo": {
                "weight_kg": self.weight_kg,
                "volume_cbm": self.volume_cbm,
                "packages": self.package_count,
                "dangerous_goods": self.is_dangerous_goods,
            },
        }

    def _resolve_currency(self, code):
        if not code:
            return self.env.company.currency_id
        currency = self.env["res.currency"].search([
            ("name", "=", code.upper()),
        ], limit=1)
        return currency or self.env.company.currency_id

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_carrier_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-CAR-004] Rate request state must change via "
                "the shop / expire actions, not direct writes."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------
    def ranked_quotes(self):
        self.ensure_one()
        quotes = self.quote_ids.filtered(lambda q: q.active)
        strategy = self.rank_strategy
        if strategy == "cheapest":
            return quotes.sorted(lambda q: (q.price, q.transit_days))
        if strategy == "fastest":
            return quotes.sorted(lambda q: (q.transit_days, q.price))
        if strategy == "preferred":
            return quotes.sorted(
                lambda q: (
                    not q.carrier_profile_id.is_preferred,
                    q.price,
                ),
            )
        # Balanced: normalise price and transit_days to [0,1] and sum.
        if not quotes:
            return quotes
        max_price = max(quotes.mapped("price")) or 1.0
        max_transit = max(quotes.mapped("transit_days")) or 1
        return quotes.sorted(
            lambda q: (q.price / max_price) + (q.transit_days / max_transit)
        )


class EhLogCarrierRateQuote(models.Model):
    _name = "eh.log.carrier.rate.quote"
    _description = "Carrier Rate Quote"
    _order = "request_id, price"

    request_id = fields.Many2one(
        "eh.log.carrier.rate.request",
        string="Request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    carrier_profile_id = fields.Many2one(
        "eh.log.carrier.profile",
        string="Carrier",
        required=True,
        ondelete="restrict",
        index=True,
    )
    service_name = fields.Char(string="Service")
    transit_days = fields.Integer(string="Transit Days")
    price = fields.Monetary(
        string="Price",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
    )
    valid_until = fields.Date(string="Valid Until")
    carrier_quote_reference = fields.Char(string="Carrier Quote Reference")
    raw_response = fields.Text(string="Raw Response")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_carrier_internal_quote_create"):
            raise UserError(_(
                "[EHL-CAR-005] Rate quotes are created by the rate-"
                "shop fan-out, not by direct ORM write."
            ))
        return super().create(vals_list)

    def write(self, vals):
        # Active flag is mutable so a quote can be archived; everything
        # else is locked once the carrier returned a price.
        protected = {k for k in vals if k != "active"}
        if protected:
            raise UserError(_(
                "[EHL-CAR-006] Rate quote field(s) %(fields)s are "
                "immutable. Re-shop to get a new quote."
            ) % {"fields": ", ".join(sorted(protected))})
        return super().write(vals)
