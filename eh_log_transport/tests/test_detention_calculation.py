# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Detention hours and amount computation across pickup and delivery delays."""
from datetime import datetime

from .common import EhLogTransportTestCase


class TestDetentionCalculation(EhLogTransportTestCase):

    def test_no_detention_when_within_free_time(self):
        trip = self._build_trip(
            free_time_hours=4.0,
            demurrage_rate_per_hour=50.0,
        )
        # 1 hour late at pickup, 2 hours late at delivery: total 3 < 4 free.
        trip.pickup_actual_at = datetime(2026, 6, 1, 9, 0)
        trip.delivery_actual_at = datetime(2026, 6, 1, 20, 0)
        trip.invalidate_recordset()
        self.assertEqual(trip.detention_hours, 0.0)
        self.assertEqual(trip.detention_amount, 0.0)

    def test_detention_charged_beyond_free_time(self):
        trip = self._build_trip(
            free_time_hours=2.0,
            demurrage_rate_per_hour=50.0,
        )
        # 3 hours late at pickup + 4 hours late at delivery = 7 hours.
        # Free time 2 = 5 chargeable hours.
        trip.pickup_actual_at = datetime(2026, 6, 1, 11, 0)
        trip.delivery_actual_at = datetime(2026, 6, 1, 22, 0)
        trip.invalidate_recordset()
        self.assertAlmostEqual(trip.detention_hours, 5.0, places=1)
        self.assertAlmostEqual(trip.detention_amount, 250.0, places=2)

    def test_early_arrival_does_not_create_negative_detention(self):
        trip = self._build_trip(
            free_time_hours=0.0,
            demurrage_rate_per_hour=50.0,
        )
        trip.pickup_actual_at = datetime(2026, 6, 1, 7, 0)
        trip.delivery_actual_at = datetime(2026, 6, 1, 17, 0)
        trip.invalidate_recordset()
        self.assertEqual(trip.detention_hours, 0.0)

    def test_partial_data_does_not_compute(self):
        trip = self._build_trip(
            free_time_hours=2.0,
            demurrage_rate_per_hour=50.0,
        )
        trip.pickup_actual_at = datetime(2026, 6, 1, 11, 0)
        # delivery_actual_at not set yet
        trip.invalidate_recordset()
        # Only pickup delay counted; 3 - 2 = 1 hr chargeable = 50.
        self.assertAlmostEqual(trip.detention_hours, 1.0, places=1)
        self.assertAlmostEqual(trip.detention_amount, 50.0, places=2)
