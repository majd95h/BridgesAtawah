# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Demurrage and detention: free time gating, chargeable days, amount."""
from datetime import datetime, timedelta

from .common import EhLogContainerMgmtTestCase


class TestDndCalculation(EhLogContainerMgmtTestCase):

    def setUp(self):
        super().setUp()
        # Configure container with 7 free days, 50 per day rate.
        self.container.write({
            "free_time_days": 7,
            "dnd_rate_per_day": 50.0,
        })

    def test_zero_when_not_gated_out(self):
        self.container.invalidate_recordset()
        self.assertEqual(self.container.dnd_amount, 0.0)
        self.assertEqual(self.container.dnd_chargeable_days, 0)

    def test_zero_within_free_time(self):
        # 5 days at destination, free time 7 -> no charge
        self.container.gate_out_at = datetime.now() - timedelta(days=5)
        self.container.invalidate_recordset()
        self.assertEqual(self.container.dnd_chargeable_days, 0)
        self.assertEqual(self.container.dnd_amount, 0.0)

    def test_chargeable_after_free_time(self):
        # 12 whole days at destination, free time 7 -> 5 chargeable days.
        # A whole-day timedelta keeps the same time of day, so the calendar
        # day count is exactly 12 whatever hour the test runs at.
        self.container.gate_out_at = datetime.now() - timedelta(days=12)
        self.container.invalidate_recordset()
        self.assertEqual(self.container.dnd_chargeable_days, 5)
        self.assertEqual(self.container.dnd_amount, 250.0)

    def test_returned_at_freezes_calculation(self):
        # Container gate-out 12 days ago, returned 9 days ago.
        # Chargeable = max(0, 9 - 7) = wait actually:
        # days_at_destination = (returned_at - gate_out_at) // 86400
        # = (3 days) // 86400 = 3
        # chargeable = max(0, 3 - 7) = 0
        # Let's adjust: gate-out 30 days ago, returned 10 days ago = 20 days at dest.
        self.container.gate_out_at = datetime.now() - timedelta(days=30)
        self.container.returned_at = datetime.now() - timedelta(days=10)
        self.container.invalidate_recordset()
        self.assertEqual(self.container.days_at_destination, 20)
        self.assertEqual(self.container.dnd_chargeable_days, 13)
        self.assertEqual(self.container.dnd_amount, 650.0)

    def test_zero_rate_yields_zero_amount(self):
        self.container.gate_out_at = datetime.now() - timedelta(days=20)
        self.container.dnd_rate_per_day = 0.0
        self.container.invalidate_recordset()
        self.assertEqual(self.container.dnd_chargeable_days, 13)
        self.assertEqual(self.container.dnd_amount, 0.0)
