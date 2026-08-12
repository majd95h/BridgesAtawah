# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Attempts: count, max-attempt routing, append-only protection,
return-to-sender flow."""
from odoo.exceptions import UserError

from .common import EhLogLastMileTestCase


class TestAttemptsAndReturns(EhLogLastMileTestCase):

    def test_failed_attempt_does_not_immediately_fail(self):
        # max_attempts default 3; one failure stays out_for_delivery.
        delivery = self._add_delivery()
        delivery.action_set_out_for_delivery()
        delivery.action_mark_failed(outcome="customer_not_home")
        self.assertEqual(delivery.attempt_count, 1)
        self.assertEqual(delivery.state, "out_for_delivery")

    def test_three_failed_attempts_route_to_failed(self):
        delivery = self._add_delivery()
        delivery.action_set_out_for_delivery()
        for _ in range(3):
            delivery.action_mark_failed(outcome="customer_not_home")
            delivery.invalidate_recordset()
        self.assertEqual(delivery.attempt_count, 3)
        self.assertEqual(delivery.state, "failed")

    def test_reschedule_returns_to_scheduled(self):
        delivery = self._add_delivery()
        delivery.action_set_out_for_delivery()
        for _ in range(3):
            delivery.action_mark_failed(outcome="customer_not_home")
            delivery.invalidate_recordset()
        self.assertEqual(delivery.state, "failed")
        delivery.action_reschedule()
        self.assertEqual(delivery.state, "scheduled")

    def test_return_to_sender_after_failure(self):
        delivery = self._add_delivery()
        delivery.action_set_out_for_delivery()
        for _ in range(3):
            delivery.action_mark_failed(outcome="address_incorrect")
            delivery.invalidate_recordset()
        delivery.action_return_to_sender()
        self.assertEqual(delivery.state, "returned")
        self.assertTrue(delivery.return_to_sender)
        self.assertEqual(delivery.return_reason, "max_attempts")

    def test_attempt_immutable_after_create(self):
        delivery = self._add_delivery()
        delivery.action_set_out_for_delivery()
        delivery.action_mark_failed(outcome="customer_not_home")
        attempt = delivery.attempt_ids[0]
        with self.assertRaises(UserError) as ctx:
            attempt.write({"outcome": "delivered"})
        self.assertIn("[EHL-LM-ATT-001]", str(ctx.exception))
        # Notes is mutable.
        attempt.write({"notes": "Customer asked for evening redelivery."})
