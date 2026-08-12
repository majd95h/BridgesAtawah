# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Event log: append-only, source state transitions emit events."""
from odoo.exceptions import UserError

from .common import EhLogTrackTestCase


class TestEventLogging(EhLogTrackTestCase):

    def test_state_transition_emits_event(self):
        delivery = self._build_delivery()
        events_before = self.env["eh.log.track.event"].search_count([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ])
        delivery.action_set_out_for_delivery()
        events_after = self.env["eh.log.track.event"].search_count([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ])
        self.assertEqual(events_after - events_before, 1)
        latest = self.env["eh.log.track.event"].search([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ], order="occurred_at desc", limit=1)
        self.assertEqual(latest.code, "out_for_delivery")

    def test_full_lifecycle_emits_two_events(self):
        delivery = self._build_delivery()
        delivery.action_set_out_for_delivery()
        delivery.action_mark_delivered(recipient_name="Jane Doe")
        codes = self.env["eh.log.track.event"].search([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ]).mapped("code")
        self.assertIn("out_for_delivery", codes)
        self.assertIn("delivered", codes)

    def test_direct_create_blocked(self):
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.track.event"].create({
                "res_model": "eh.log.last.mile.delivery",
                "res_id": 1,
                "event_code_id": self.code_in_transit.id,
            })
        self.assertIn("[EHL-TRK-004]", str(ctx.exception))

    def test_event_field_immutable(self):
        delivery = self._build_delivery()
        delivery.action_set_out_for_delivery()
        event = self.env["eh.log.track.event"].search([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ], limit=1)
        with self.assertRaises(UserError) as ctx:
            event.write({"event_code_id": self.code_delivered.id})
        self.assertIn("[EHL-TRK-005]", str(ctx.exception))
        # Notes is mutable.
        event.write({"notes": "Operator annotation."})

    def test_event_unlink_blocked(self):
        delivery = self._build_delivery()
        delivery.action_set_out_for_delivery()
        event = self.env["eh.log.track.event"].search([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ], limit=1)
        with self.assertRaises(UserError) as ctx:
            event.unlink()
        self.assertIn("[EHL-TRK-006]", str(ctx.exception))

    def test_unknown_code_rejected(self):
        delivery = self._build_delivery()
        with self.assertRaises(ValueError) as ctx:
            delivery.log_track_event("not_a_code")
        self.assertIn("[EHL-TRK-001]", str(ctx.exception))

    def test_to_public_dict_strips_internals(self):
        delivery = self._build_delivery()
        delivery.action_set_out_for_delivery()
        event = self.env["eh.log.track.event"].search([
            ("res_model", "=", "eh.log.last.mile.delivery"),
            ("res_id", "=", delivery.id),
        ], limit=1)
        public = event.to_public_dict()
        self.assertNotIn("raw_payload", public)
        self.assertNotIn("notes", public)
        self.assertNotIn("source", public)
        self.assertIn("code", public)
        self.assertIn("label", public)
