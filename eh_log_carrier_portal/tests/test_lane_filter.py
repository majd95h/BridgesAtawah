# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Lane filter: matches and skips correctly during fan-out."""
from .common import EhLogCarrierTestCase


class TestLaneFilter(EhLogCarrierTestCase):

    def test_matching_lane_does_not_skip_carrier(self):
        self.env["eh.log.carrier.lane"].create({
            "carrier_profile_id": self.ocean.id,
            "origin_country_id": self.country_in.id,
            "destination_country_id": self.country_ae.id,
        })
        request = self._build_request(mode="ocean")
        request.shop()
        self.assertTrue(request.quote_ids)

    def test_non_matching_lane_skips_carrier(self):
        # Lane is set to a route the request does not match.
        country_other = self.env.ref("base.us")
        self.env["eh.log.carrier.lane"].create({
            "carrier_profile_id": self.ocean.id,
            "origin_country_id": country_other.id,
            "destination_country_id": country_other.id,
        })
        request = self._build_request(mode="ocean")
        request.shop()
        self.assertFalse(request.quote_ids)

    def test_lane_matches_helper(self):
        lane = self.env["eh.log.carrier.lane"].create({
            "carrier_profile_id": self.ocean.id,
            "origin_country_id": self.country_in.id,
            "origin_location_code": "INMUN",
            "destination_country_id": self.country_ae.id,
            "destination_location_code": "AEJEA",
        })
        self.assertTrue(lane.matches("IN", "AE", "INMUN", "AEJEA"))
        self.assertFalse(lane.matches("IN", "AE", "INNAS", "AEJEA"))
        self.assertFalse(lane.matches("US", "AE"))
