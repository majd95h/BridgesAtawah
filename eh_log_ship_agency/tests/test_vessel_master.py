# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Vessel master: IMO checksum, MMSI format, berth compatibility."""
from odoo.exceptions import ValidationError

from .common import EhLogShipTestCase, TEST_IMO_ALT


class TestVesselMaster(EhLogShipTestCase):

    def test_imo_invalid_checksum_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.ship.vessel"].create({
                "name": "Bad",
                "imo_number": "9074721",  # checksum is wrong
                "vessel_type": "container",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-SHP-001]", str(ctx.exception))

    def test_imo_too_short_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.ship.vessel"].create({
                "name": "Bad",
                "imo_number": "12345",
                "vessel_type": "container",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-SHP-001]", str(ctx.exception))

    def test_alt_imo_accepted(self):
        # Confirms a second known-good IMO works.
        vessel = self.env["eh.log.ship.vessel"].create({
            "name": "Alt Vessel",
            "imo_number": TEST_IMO_ALT,
            "vessel_type": "bulk",
            "company_id": self.company.id,
        })
        self.assertTrue(vessel.id)

    def test_mmsi_must_be_nine_digits(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.ship.vessel"].create({
                "name": "Bad MMSI",
                "imo_number": TEST_IMO_ALT,
                "vessel_type": "container",
                "mmsi": "12345",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-SHP-002]", str(ctx.exception))

    def test_berth_compatibility_passes_for_compatible(self):
        problems = self.berth.check_compatibility(self.vessel)
        self.assertEqual(problems, [])

    def test_berth_rejects_too_deep(self):
        deep_vessel = self.env["eh.log.ship.vessel"].create({
            "name": "Too Deep",
            "imo_number": TEST_IMO_ALT,
            "vessel_type": "tanker",
            "draft_m": 18.0,
            "company_id": self.company.id,
        })
        problems = self.berth.check_compatibility(deep_vessel)
        self.assertTrue(any("draft" in p.lower() for p in problems))

    def test_berth_rejects_too_long(self):
        long_vessel = self.env["eh.log.ship.vessel"].create({
            "name": "Too Long",
            "imo_number": TEST_IMO_ALT,
            "vessel_type": "container",
            "length_overall_m": 400.0,
            "company_id": self.company.id,
        })
        problems = self.berth.check_compatibility(long_vessel)
        self.assertTrue(any("loa" in p.lower() for p in problems))
