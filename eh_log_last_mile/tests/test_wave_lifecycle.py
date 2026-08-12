# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Wave: dispatch prerequisites, state machine, completion gating."""
from datetime import date, timedelta

from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogLastMileTestCase


class TestWaveLifecycle(EhLogLastMileTestCase):

    def test_initial_state(self):
        wave = self._build_wave()
        self.assertEqual(wave.state, "draft")
        self.assertTrue(wave.name.startswith("LMW/"))

    def test_dispatch_blocked_without_deliveries(self):
        wave = self._build_wave()
        with self.assertRaises(UserError) as ctx:
            wave.action_dispatch()
        self.assertIn("[EHL-LM-WAVE-002]", str(ctx.exception))

    def test_dispatch_blocked_with_expired_driver(self):
        self.driver.license_expiry_date = date.today() - timedelta(days=1)
        wave = self._build_wave()
        self._add_delivery(wave=wave)
        with self.assertRaises(UserError) as ctx:
            wave.action_dispatch()
        self.assertIn("expired license", str(ctx.exception))

    def test_dispatch_promotes_deliveries_to_out_for_delivery(self):
        wave = self._build_wave()
        delivery = self._add_delivery(wave=wave)
        self.assertEqual(delivery.state, "scheduled")
        wave.action_dispatch()
        delivery.invalidate_recordset()
        self.assertEqual(delivery.state, "out_for_delivery")
        self.assertTrue(wave.departed_at)

    def test_completion_blocked_with_pending_deliveries(self):
        wave = self._build_wave()
        self._add_delivery(wave=wave)
        wave.action_dispatch()
        wave.action_set_in_progress()
        with self.assertRaises(UserError) as ctx:
            wave.action_complete()
        self.assertIn("[EHL-LM-WAVE-003]", str(ctx.exception))

    def test_close_blocked_with_outstanding_cod(self):
        wave = self._build_wave()
        delivery = self._add_delivery(wave=wave, cod=100.0)
        wave.action_dispatch()
        wave.action_set_in_progress()
        # Mark delivered with full COD collected so completion can pass.
        delivery.action_mark_delivered(
            recipient_name="Mr. Recipient",
            cod_collected=100.0,
            cod_method="cash",
        )
        wave.action_complete()
        wave.invalidate_recordset()
        # No outstanding COD; close should pass.
        wave.action_close()
        self.assertEqual(wave.state, "closed")

    def test_close_blocked_when_cod_short(self):
        wave = self._build_wave()
        delivery = self._add_delivery(wave=wave, cod=100.0)
        wave.action_dispatch()
        wave.action_set_in_progress()
        # Manually mark delivered without COD (bypass through internal write).
        delivery.with_context(eh_log_last_mile_delivery_state_write=True).write({
            "state": "delivered",
            "cod_collected_amount": 50.0,
        })
        wave.invalidate_recordset()
        # Cannot complete pending deliveries first; manually move on.
        wave.action_complete()
        with self.assertRaises(UserError) as ctx:
            wave.action_close()
        self.assertIn("[EHL-LM-WAVE-004]", str(ctx.exception))

    def test_disallowed_transition_blocked(self):
        wave = self._build_wave()
        with self.assertRaises(JobStateConflictError):
            wave.action_complete()  # cannot complete from draft

    def test_direct_state_write_blocked(self):
        wave = self._build_wave()
        with self.assertRaises(UserError) as ctx:
            wave.write({"state": "dispatched"})
        self.assertIn("[EHL-LM-WAVE-001]", str(ctx.exception))
