# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Facility / zone / location masters."""
from odoo.exceptions import UserError, ValidationError

from .common import EhLogWarehouseTestCase


class TestFacilitySetup(EhLogWarehouseTestCase):

    def test_facility_code_alnum_required(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.warehouse.facility"].create({
                "name": "Bad", "code": "BAD CODE",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-WHS-001]", str(ctx.exception))

    def test_zone_code_alnum_required(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.warehouse.zone"].create({
                "name": "Bad", "code": "B@D",
                "facility_id": self.facility.id,
                "purpose": "bonded",
            })
        self.assertIn("[EHL-WHS-002]", str(ctx.exception))

    def test_location_full_code_composes(self):
        self.assertEqual(
            self.location.full_code,
            "TBW/BB/A0101",
        )

    def test_facility_zone_count(self):
        self.assertGreaterEqual(self.facility.zone_count, 2)

    def test_client_billing_day_in_range(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.warehouse.client"].create({
                "name": "Bad",
                "code": "BAD",
                "partner_id": self.partner.id,
                "rate_card_id": self.rate_card.id,
                "billing_day": 31,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-WHS-004]", str(ctx.exception))
