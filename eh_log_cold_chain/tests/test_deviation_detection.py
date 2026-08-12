# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Deviation detector: alert window, kind, resolution flow."""
from datetime import datetime

from odoo.exceptions import UserError

from .common import EhLogColdChainTestCase


class TestDeviationDetection(EhLogColdChainTestCase):

    def setUp(self):
        super().setUp()
        # The PHARMA-2-8 profile: alert window 30 min.
        self.run = self._build_run(self.profile_pharma)
        self.run.action_activate()
        self.base = datetime(2026, 6, 1, 10, 0)

    def test_no_deviation_for_in_window_breach(self):
        # Single 15-minute spike: shorter than the 30-min alert window.
        # Three readings: t=0 (4 degC), t=15 (10 degC, breach), t=30 (5 degC).
        # The breach segment is from t=15 to t=30 = 15 minutes < 30 alert window.
        samples = [
            (self.base, 4.0),
            (self._seconds_apart(self.base, 15), 10.0),
            (self._seconds_apart(self.base, 30), 5.0),
        ]
        self.run.ingest_readings(samples)
        self.run.invalidate_recordset()
        self.assertEqual(len(self.run.deviation_ids), 0)

    def test_deviation_raised_on_sustained_high_breach(self):
        # Sustained high breach: t=0 to t=60 above max.
        samples = [
            (self.base, 4.5),
            (self._seconds_apart(self.base, 15), 10.0),  # breach
            (self._seconds_apart(self.base, 30), 11.0),  # breach
            (self._seconds_apart(self.base, 45), 12.0),  # breach
            (self._seconds_apart(self.base, 60), 11.5),  # breach
            (self._seconds_apart(self.base, 75), 5.0),  # back in
        ]
        self.run.ingest_readings(samples)
        self.run.invalidate_recordset()
        self.assertEqual(len(self.run.deviation_ids), 1)
        dev = self.run.deviation_ids
        self.assertEqual(dev.deviation_kind, "high")
        self.assertAlmostEqual(dev.max_temperature, 12.0, places=2)
        self.assertAlmostEqual(dev.min_temperature, 10.0, places=2)

    def test_deviation_raised_on_sustained_low_breach(self):
        samples = [
            (self.base, 5.0),
            (self._seconds_apart(self.base, 15), 0.0),
            (self._seconds_apart(self.base, 30), -1.0),
            (self._seconds_apart(self.base, 45), -2.0),
            (self._seconds_apart(self.base, 60), -1.5),
            (self._seconds_apart(self.base, 75), 4.0),
        ]
        self.run.ingest_readings(samples)
        self.run.invalidate_recordset()
        self.assertEqual(len(self.run.deviation_ids), 1)
        dev = self.run.deviation_ids
        self.assertEqual(dev.deviation_kind, "low")

    def test_deviation_state_machine(self):
        samples = [
            (self.base, 4.5),
            (self._seconds_apart(self.base, 15), 10.0),
            (self._seconds_apart(self.base, 30), 11.0),
            (self._seconds_apart(self.base, 45), 12.0),
            (self._seconds_apart(self.base, 60), 11.5),
            (self._seconds_apart(self.base, 75), 5.0),
        ]
        self.run.ingest_readings(samples)
        self.run.invalidate_recordset()
        dev = self.run.deviation_ids
        self.assertEqual(dev.state, "open")
        dev.action_acknowledge()
        self.assertEqual(dev.state, "acknowledged")
        self.assertEqual(dev.acknowledged_by_id, self.env.user)
        # Resolution requires a cause first.
        with self.assertRaises(UserError) as ctx:
            dev.action_resolve()
        self.assertIn("cause classification", str(ctx.exception))
        dev.cause = "equipment_failure"
        dev.action_resolve()
        self.assertEqual(dev.state, "resolved")
        self.assertEqual(dev.resolved_by_id, self.env.user)

    def test_void_requires_resolution_notes(self):
        samples = [
            (self.base, 5.0),
            (self._seconds_apart(self.base, 15), 11.0),
            (self._seconds_apart(self.base, 30), 11.5),
            (self._seconds_apart(self.base, 45), 12.0),
            (self._seconds_apart(self.base, 60), 11.5),
            (self._seconds_apart(self.base, 75), 5.0),
        ]
        self.run.ingest_readings(samples)
        dev = self.run.deviation_ids
        with self.assertRaises(UserError) as ctx:
            dev.action_void()
        self.assertIn("[EHL-COLD-CHAIN-DEV-003]", str(ctx.exception))
        dev.resolution_notes = "Sensor was placed too close to the door."
        dev.action_void()
        self.assertEqual(dev.state, "voided")

    def test_cargo_impacting_drives_breached_completion(self):
        samples = [
            (self.base, 5.0),
            (self._seconds_apart(self.base, 15), 11.0),
            (self._seconds_apart(self.base, 30), 11.5),
            (self._seconds_apart(self.base, 45), 12.0),
            (self._seconds_apart(self.base, 60), 11.5),
            (self._seconds_apart(self.base, 75), 5.0),
        ]
        self.run.ingest_readings(samples)
        self.run.invalidate_recordset()
        dev = self.run.deviation_ids
        dev.action_mark_cargo_impacting()
        self.run.invalidate_recordset()
        self.assertFalse(self.run.is_compliant)
        self.run.action_complete()
        self.assertEqual(self.run.state, "breached")

    def test_compliant_when_no_cargo_impacting_deviation(self):
        # Even with a deviation, if not cargo-impacting, the run is
        # still considered compliant.
        samples = [
            (self.base, 5.0),
            (self._seconds_apart(self.base, 15), 11.0),
            (self._seconds_apart(self.base, 30), 11.5),
            (self._seconds_apart(self.base, 45), 12.0),
            (self._seconds_apart(self.base, 60), 11.5),
            (self._seconds_apart(self.base, 75), 5.0),
        ]
        self.run.ingest_readings(samples)
        self.run.invalidate_recordset()
        # Don't flag as cargo-impacting.
        self.assertTrue(self.run.is_compliant)
        self.run.action_complete()
        self.assertEqual(self.run.state, "completed")
