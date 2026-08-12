# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Trip state machine, dispatch prerequisites, ePOD count."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogTransportTestCase


class TestTripLifecycle(EhLogTransportTestCase):

    def setUp(self):
        super().setUp()
        self.trip = self._build_trip()

    def test_initial_state_is_planned(self):
        self.assertEqual(self.trip.state, "planned")
        self.assertTrue(self.trip.name.startswith("TRP/"))

    def test_full_happy_path(self):
        self.trip.action_dispatch()
        self.assertEqual(self.trip.state, "dispatched")
        self.trip.action_set_at_pickup()
        self.assertEqual(self.trip.state, "at_pickup")
        self.assertTrue(self.trip.pickup_actual_at)
        self.trip.action_set_in_transit()
        self.assertEqual(self.trip.state, "in_transit")
        self.trip.action_set_at_delivery()
        self.assertEqual(self.trip.state, "at_delivery")
        self.trip.action_set_delivered()
        self.assertEqual(self.trip.state, "delivered")
        self.assertTrue(self.trip.delivery_actual_at)
        self.trip.action_close()
        self.assertEqual(self.trip.state, "closed")

    def test_dispatch_blocked_without_vehicle(self):
        self.trip.vehicle_id = False
        with self.assertRaises(UserError) as ctx:
            self.trip.action_dispatch()
        self.assertIn("[EHL-TRIP-001]", str(ctx.exception))
        self.assertIn("Vehicle is not assigned", str(ctx.exception))

    def test_dispatch_blocked_without_driver(self):
        self.trip.driver_id = False
        with self.assertRaises(UserError):
            self.trip.action_dispatch()

    def test_dispatch_blocked_without_planned_times(self):
        self.trip.pickup_planned_at = False
        with self.assertRaises(UserError):
            self.trip.action_dispatch()

    def test_disallowed_transition_blocked(self):
        with self.assertRaises(JobStateConflictError):
            self.trip.action_set_delivered()

    def test_direct_state_write_blocked(self):
        with self.assertRaises(UserError) as ctx:
            self.trip.write({"state": "dispatched"})
        self.assertIn("[EHL-TRIP-002]", str(ctx.exception))

    def test_pod_count_updates(self):
        self.assertEqual(self.trip.pod_count, 0)
        self.env["eh.log.transport.pod"].create({
            "trip_id": self.trip.id,
            "recipient_name": "John Smith",
        })
        self.trip.invalidate_recordset()
        self.assertEqual(self.trip.pod_count, 1)
