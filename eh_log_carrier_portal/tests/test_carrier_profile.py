# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Carrier profile: provider validation, adapter resolution."""
from odoo.exceptions import UserError, ValidationError

from .common import EhLogCarrierTestCase


class TestCarrierProfile(EhLogCarrierTestCase):

    def test_provider_must_be_registered(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.carrier.profile"].create({
                "name": "Bogus Carrier",
                "code": "BOG",
                "mode": "ocean",
                "provider_code": "no_such_provider",
                "credentials_key": "x",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-CAR-001]", str(ctx.exception))

    def test_get_adapter_returns_instance(self):
        adapter = self.ocean.get_adapter()
        self.assertEqual(adapter.PROVIDER_CODE, "mock_ocean")

    def test_health_check_returns_ok(self):
        adapter = self.ocean.get_adapter()
        result = adapter.health_check()
        self.assertTrue(result.ok)

    def test_lane_count_compute(self):
        self.assertEqual(self.ocean.lane_count, 0)
        self.env["eh.log.carrier.lane"].create({
            "carrier_profile_id": self.ocean.id,
            "origin_country_id": self.country_in.id,
            "destination_country_id": self.country_ae.id,
        })
        self.ocean.invalidate_recordset()
        self.assertEqual(self.ocean.lane_count, 1)
