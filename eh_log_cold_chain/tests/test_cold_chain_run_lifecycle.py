# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Cold chain run state machine, write protection, sale.order spawn."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogColdChainTestCase


class TestColdChainRunLifecycle(EhLogColdChainTestCase):

    def test_run_auto_spawned_on_freight_job_creation(self):
        # The setUp builds an order with cold chain required; the freight
        # job spawn should have auto-created the run.
        runs = self.job.cold_chain_run_ids
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs.profile_id, self.profile_pharma)
        self.assertEqual(runs.state, "draft")

    def test_full_happy_path(self):
        run = self._build_run()
        run.action_activate()
        self.assertEqual(run.state, "active")
        self.assertTrue(run.started_at)
        run.action_complete()
        # No deviations recorded; should land in completed (compliant)
        self.assertEqual(run.state, "completed")
        self.assertTrue(run.completed_at)

    def test_disallowed_transition_blocked(self):
        run = self._build_run()
        with self.assertRaises(JobStateConflictError):
            run.action_complete()  # cannot complete from draft

    def test_direct_state_write_blocked(self):
        run = self._build_run()
        with self.assertRaises(UserError) as ctx:
            run.write({"state": "active"})
        self.assertIn("[EHL-COLD-CHAIN-001]", str(ctx.exception))

    def test_ingest_requires_active_state(self):
        from datetime import datetime
        run = self._build_run()
        with self.assertRaises(UserError) as ctx:
            run.ingest_readings([(datetime(2026, 6, 1, 10, 0), 5.0)])
        self.assertIn("[EHL-COLD-CHAIN-002]", str(ctx.exception))

    def test_ingest_creates_readings_and_updates_aggregates(self):
        from datetime import datetime
        run = self._build_run()
        run.action_activate()
        base = datetime(2026, 6, 1, 10, 0)
        samples = [
            (base, 4.5),
            (self._seconds_apart(base, 15), 5.2),
            (self._seconds_apart(base, 30), 6.0),
            (self._seconds_apart(base, 45), 7.1),
            (self._seconds_apart(base, 60), 4.8),
        ]
        run.ingest_readings(samples)
        run.invalidate_recordset()
        self.assertEqual(run.reading_count, 5)
        self.assertAlmostEqual(run.min_temperature, 4.5, places=2)
        self.assertAlmostEqual(run.max_temperature, 7.1, places=2)


class TestColdChainReadingAppendOnly(EhLogColdChainTestCase):

    def test_reading_temperature_immutable_after_create(self):
        from datetime import datetime
        run = self._build_run()
        run.action_activate()
        reading = self.env["eh.log.cold.chain.reading"].create({
            "run_id": run.id,
            "captured_at": datetime(2026, 6, 1, 10, 0),
            "temperature": 5.0,
        })
        with self.assertRaises(UserError) as ctx:
            reading.temperature = 6.0
        self.assertIn("[EHL-COLD-CHAIN-READING-001]", str(ctx.exception))
        # Source and sensor_reference are mutable; should not raise.
        reading.write({"sensor_reference": "SENSOR-A1", "source": "telematics"})
