# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Delivery: state machine, mark-delivered, defaults."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogLastMileTestCase


class TestDeliveryLifecycle(EhLogLastMileTestCase):

    def test_initial_state(self):
        delivery = self._add_delivery()
        self.assertEqual(delivery.state, "scheduled")
        self.assertTrue(delivery.name.startswith("LMD/"))

    def test_default_delivery_partner_falls_back_to_customer(self):
        delivery = self._add_delivery()
        self.assertEqual(delivery.delivery_partner_id, self.customer_a)

    def test_full_delivery_path(self):
        delivery = self._add_delivery()
        delivery.action_set_out_for_delivery()
        self.assertEqual(delivery.state, "out_for_delivery")
        delivery.action_mark_delivered(
            recipient_name="Mr. Recipient",
            recipient_role="Receptionist",
        )
        self.assertEqual(delivery.state, "delivered")
        self.assertTrue(delivery.delivered_at)
        self.assertEqual(delivery.recipient_name, "Mr. Recipient")
        # An auto-attempt was logged.
        self.assertEqual(delivery.attempt_count, 1)

    def test_disallowed_transition_blocked(self):
        delivery = self._add_delivery()
        with self.assertRaises(JobStateConflictError):
            delivery.action_mark_delivered(recipient_name="X")

    def test_direct_state_write_blocked(self):
        delivery = self._add_delivery()
        with self.assertRaises(UserError) as ctx:
            delivery.write({"state": "delivered"})
        self.assertIn("[EHL-LM-DEL-001]", str(ctx.exception))
