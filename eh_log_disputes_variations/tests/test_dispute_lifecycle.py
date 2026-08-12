# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dispute: state machine, financial validation, exposure compute."""
from odoo.exceptions import UserError, ValidationError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogDisputesTestCase


class TestDisputeLifecycle(EhLogDisputesTestCase):

    def test_initial_state_and_sequence(self):
        dispute = self._build_dispute()
        self.assertEqual(dispute.state, "opened")
        self.assertTrue(dispute.name.startswith("DSP/"))

    def test_full_path_to_settlement(self):
        dispute = self._build_dispute(claimed=2000.0)
        dispute.action_start_investigation()
        self.assertEqual(dispute.state, "investigating")
        dispute.action_make_offer(amount=1500.0)
        self.assertEqual(dispute.state, "offered")
        self.assertEqual(dispute.offered_amount, 1500.0)
        dispute.action_accept_offer()
        self.assertEqual(dispute.state, "accepted")
        dispute.action_settle()
        self.assertEqual(dispute.state, "settled")
        # Settled amount defaulted from offered.
        self.assertEqual(dispute.settled_amount, 1500.0)
        dispute.action_close()
        self.assertEqual(dispute.state, "closed")

    def test_offer_cannot_exceed_claim(self):
        dispute = self._build_dispute(claimed=500.0)
        dispute.action_start_investigation()
        with self.assertRaises(ValidationError) as ctx:
            dispute.action_make_offer(amount=1000.0)
        self.assertIn("[EHL-DSP-005]", str(ctx.exception))

    def test_offer_requires_amount(self):
        dispute = self._build_dispute(claimed=500.0)
        dispute.action_start_investigation()
        with self.assertRaises(UserError) as ctx:
            dispute.action_make_offer()
        self.assertIn("[EHL-DSP-006]", str(ctx.exception))

    def test_settle_requires_amount(self):
        dispute = self._build_dispute(claimed=500.0)
        dispute.action_start_investigation()
        # Force into accepted without an offer (would not normally
        # happen but we test the guard).
        dispute.offered_amount = 100.0
        dispute.action_make_offer(amount=100.0)
        dispute.action_accept_offer()
        dispute.offered_amount = 0.0
        with self.assertRaises(UserError) as ctx:
            dispute.action_settle()
        self.assertIn("[EHL-DSP-007]", str(ctx.exception))

    def test_state_direct_write_blocked(self):
        dispute = self._build_dispute()
        with self.assertRaises(UserError) as ctx:
            dispute.write({"state": "settled"})
        self.assertIn("[EHL-DSP-008]", str(ctx.exception))

    def test_disallowed_transition(self):
        dispute = self._build_dispute()
        with self.assertRaises(JobStateConflictError):
            dispute.action_settle()  # cannot settle from opened

    def test_exposure_compute(self):
        dispute = self._build_dispute(claimed=1000.0)
        # Initial: claimed (no offer, no settle).
        self.assertEqual(dispute.exposure, 1000.0)
        dispute.action_start_investigation()
        dispute.action_make_offer(amount=750.0)
        dispute.invalidate_recordset()
        # Once an offer is on the table, exposure tracks the offer.
        self.assertEqual(dispute.exposure, 750.0)
        dispute.action_accept_offer()
        dispute.action_settle()
        dispute.invalidate_recordset()
        self.assertEqual(dispute.exposure, 750.0)

    def test_write_off_path(self):
        dispute = self._build_dispute(claimed=1000.0)
        dispute.action_start_investigation()
        dispute.action_make_offer(amount=500.0)
        dispute.action_escalate()
        dispute.action_write_off()
        self.assertEqual(dispute.state, "written_off")
        self.assertEqual(dispute.settled_amount, 0.0)
