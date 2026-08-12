# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""SOF events: append-only, manual annotation, transition emission."""
from odoo.exceptions import UserError

from .common import EhLogShipTestCase


class TestSofEvents(EhLogShipTestCase):

    def test_state_transition_emits_event(self):
        call = self._build_port_call()
        call.action_mark_arrived()
        events = call.sof_event_ids
        self.assertTrue(events)
        self.assertIn("arrived", events.mapped("description")[-1].lower())

    def test_event_field_immutable(self):
        call = self._build_port_call()
        call.action_mark_arrived()
        event = call.sof_event_ids[:1]
        with self.assertRaises(UserError) as ctx:
            event.write({"description": "tampered"})
        self.assertIn("[EHL-SHP-010]", str(ctx.exception))
        # Notes is mutable.
        event.write({"notes": "Annotated by ops on the next morning."})

    def test_event_unlink_blocked(self):
        call = self._build_port_call()
        call.action_mark_arrived()
        event = call.sof_event_ids[:1]
        with self.assertRaises(UserError) as ctx:
            event.unlink()
        self.assertIn("[EHL-SHP-011]", str(ctx.exception))

    def test_manual_event_creation_allowed(self):
        call = self._build_port_call()
        event = self.env["eh.log.ship.sof.event"].create({
            "port_call_id": call.id,
            "description": "Pilot on board",
            "event_category": "operational",
            "company_id": self.company.id,
        })
        self.assertEqual(event.port_call_id, call)
