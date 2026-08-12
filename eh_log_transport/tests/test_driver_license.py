# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Driver license expiry flag and dispatch gating."""
from datetime import date, timedelta

from odoo.exceptions import UserError

from .common import EhLogTransportTestCase


class TestDriverLicense(EhLogTransportTestCase):

    def test_active_license_not_expired(self):
        self.assertFalse(self.driver.is_license_expired)

    def test_expired_license_flagged(self):
        self.driver.license_expiry_date = date.today() - timedelta(days=1)
        self.driver.invalidate_recordset()
        self.assertTrue(self.driver.is_license_expired)

    def test_dispatch_blocked_with_expired_license(self):
        self.driver.license_expiry_date = date.today() - timedelta(days=1)
        trip = self._build_trip()
        with self.assertRaises(UserError) as ctx:
            trip.action_dispatch()
        self.assertIn("[EHL-TRIP-001]", str(ctx.exception))
        self.assertIn("expired license", str(ctx.exception))

    def test_partner_auto_created_for_driver(self):
        new_driver = self.env["eh.log.transport.driver"].create({
            "name": "Auto Partner Driver",
            "license_number": "L-AUTO-001",
        })
        self.assertTrue(new_driver.partner_id)
        self.assertEqual(new_driver.partner_id.name, "Auto Partner Driver")
