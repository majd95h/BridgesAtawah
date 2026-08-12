# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Rate shop: fan-out, quote persistence, ranking, immutability."""
from odoo.exceptions import UserError

from .common import EhLogCarrierTestCase


class TestRateShop(EhLogCarrierTestCase):

    def test_shop_persists_quotes(self):
        request = self._build_request(mode="ocean")
        request.shop()
        self.assertEqual(request.state, "shopped")
        # Mock ocean returns 2 service variants per call.
        self.assertEqual(len(request.quote_ids), 2)
        for quote in request.quote_ids:
            self.assertGreater(quote.price, 0)
            self.assertGreater(quote.transit_days, 0)

    def test_shop_ocean_only_consults_ocean_carriers(self):
        request = self._build_request(mode="ocean")
        request.shop()
        carriers = request.quote_ids.mapped("carrier_profile_id")
        self.assertEqual(carriers, self.ocean)
        self.assertNotIn(self.air, carriers)

    def test_shop_air_only_consults_air_carriers(self):
        request = self._build_request(mode="air")
        request.shop()
        carriers = request.quote_ids.mapped("carrier_profile_id")
        self.assertEqual(carriers, self.air)
        self.assertNotIn(self.ocean, carriers)

    def test_quote_direct_create_blocked(self):
        request = self._build_request(mode="ocean")
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.carrier.rate.quote"].create({
                "request_id": request.id,
                "carrier_profile_id": self.ocean.id,
                "price": 1.0,
                "currency_id": self.env.company.currency_id.id,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-CAR-005]", str(ctx.exception))

    def test_quote_field_immutable(self):
        request = self._build_request(mode="ocean")
        request.shop()
        quote = request.quote_ids[:1]
        with self.assertRaises(UserError) as ctx:
            quote.write({"price": 1.0})
        self.assertIn("[EHL-CAR-006]", str(ctx.exception))
        # Active flag still mutable.
        quote.write({"active": False})

    def test_ranking_cheapest(self):
        request = self._build_request(mode="ocean")
        request.shop()
        request.rank_strategy = "cheapest"
        ranked = request.ranked_quotes()
        prices = ranked.mapped("price")
        self.assertEqual(prices, sorted(prices))

    def test_ranking_fastest(self):
        request = self._build_request(mode="ocean")
        request.shop()
        request.rank_strategy = "fastest"
        ranked = request.ranked_quotes()
        days = ranked.mapped("transit_days")
        self.assertEqual(days, sorted(days))

    def test_state_direct_write_blocked(self):
        request = self._build_request(mode="ocean")
        with self.assertRaises(UserError) as ctx:
            request.write({"state": "shopped"})
        self.assertIn("[EHL-CAR-004]", str(ctx.exception))
