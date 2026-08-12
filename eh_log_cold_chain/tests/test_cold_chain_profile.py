# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Cold chain profile constraints and seed integrity."""
from psycopg2 import IntegrityError
from odoo.tools.misc import mute_logger

from odoo.addons.eh_log_base.exceptions import EhLogValidationError

from .common import EhLogColdChainTestCase


SEED_PROFILES = ["PHARMA-2-8", "CHILLED", "FROZEN-18", "DEEP-FROZEN-45", "AMB-15-25", "DRY-ICE"]


class TestColdChainProfile(EhLogColdChainTestCase):

    def test_seed_profiles_present(self):
        Profile = self.env["eh.log.cold.chain.profile"]
        for code in SEED_PROFILES:
            record = Profile.search([("code", "=", code)])
            self.assertEqual(
                len(record), 1,
                f"Seed profile {code} missing or duplicated.",
            )

    def test_profile_code_unique(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["eh.log.cold.chain.profile"].create({
                    "code": "PHARMA-2-8",
                    "name": "Duplicate",
                    "category": "pharma",
                    "temperature_min": 2.0,
                    "temperature_max": 8.0,
                })

    def test_temperature_range_constraint(self):
        with self.assertRaises(EhLogValidationError) as ctx:
            self.env["eh.log.cold.chain.profile"].create({
                "code": "INVALID",
                "name": "Inverted range",
                "category": "custom",
                "temperature_min": 10.0,
                "temperature_max": 5.0,
            })
        self.assertIn("[EHL-BASE-120]", str(ctx.exception))

    def test_humidity_range_constraint_when_monitoring(self):
        with self.assertRaises(EhLogValidationError) as ctx:
            self.env["eh.log.cold.chain.profile"].create({
                "code": "INVALID-HUM",
                "name": "Inverted humidity",
                "category": "custom",
                "temperature_min": 2.0,
                "temperature_max": 8.0,
                "monitor_humidity": True,
                "humidity_min": 80.0,
                "humidity_max": 30.0,
            })
        self.assertIn("[EHL-BASE-121]", str(ctx.exception))

    def test_humidity_range_not_enforced_when_not_monitoring(self):
        # Same out-of-order values should pass when humidity monitoring off.
        record = self.env["eh.log.cold.chain.profile"].create({
            "code": "OK-NO-HUM",
            "name": "OK without humidity",
            "category": "custom",
            "temperature_min": 2.0,
            "temperature_max": 8.0,
            "monitor_humidity": False,
            "humidity_min": 80.0,
            "humidity_max": 30.0,
        })
        self.assertTrue(record.id)
