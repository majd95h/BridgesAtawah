# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Booking: state machine, carrier ref capture, cancellation."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogCarrierTestCase


class TestBookingLifecycle(EhLogCarrierTestCase):

    def _shop_and_book(self):
        request = self._build_request(mode="ocean")
        request.shop()
        quote = request.ranked_quotes()[:1]
        booking = self.env["eh.log.carrier.booking"].create({
            "quote_id": quote.id,
            "company_id": self.company.id,
        })
        return booking

    def test_initial_state_requested(self):
        booking = self._shop_and_book()
        self.assertEqual(booking.state, "requested")
        self.assertTrue(booking.name.startswith("BKG/"))

    def test_request_books_and_captures_carrier_ref(self):
        booking = self._shop_and_book()
        booking.action_request()
        self.assertEqual(booking.state, "accepted")
        self.assertTrue(booking.carrier_booking_reference)
        self.assertTrue(booking.accepted_at)

    def test_full_lifecycle(self):
        booking = self._shop_and_book()
        booking.action_request()
        booking.action_confirm()
        self.assertEqual(booking.state, "confirmed")
        self.assertTrue(booking.confirmed_at)
        booking.action_close()
        self.assertEqual(booking.state, "closed")

    def test_state_direct_write_blocked(self):
        booking = self._shop_and_book()
        with self.assertRaises(UserError) as ctx:
            booking.write({"state": "confirmed"})
        self.assertIn("[EHL-CAR-010]", str(ctx.exception))

    def test_disallowed_transition_blocked(self):
        booking = self._shop_and_book()
        with self.assertRaises(JobStateConflictError):
            booking.action_close()  # cannot close from requested

    def test_cancel_from_accepted(self):
        booking = self._shop_and_book()
        booking.action_request()
        booking.action_cancel()
        self.assertEqual(booking.state, "cancelled")
        self.assertTrue(booking.cancelled_at)
