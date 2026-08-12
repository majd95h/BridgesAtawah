# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dispute events: append-only enforcement + open-on-create event."""
from odoo.exceptions import UserError

from .common import EhLogDisputesTestCase


class TestDisputeEventLog(EhLogDisputesTestCase):

    def test_open_event_logged_on_create(self):
        dispute = self._build_dispute()
        events = dispute.event_ids
        self.assertTrue(events)
        self.assertEqual(events[0].event_type, "opened")

    def test_state_transition_emits_event(self):
        dispute = self._build_dispute()
        before = len(dispute.event_ids)
        dispute.action_start_investigation()
        dispute.invalidate_recordset()
        self.assertGreater(len(dispute.event_ids), before)
        latest = dispute.event_ids.sorted(lambda e: e.id, reverse=True)[0]
        self.assertEqual(latest.event_type, "state_change")
        self.assertEqual(latest.from_state, "opened")
        self.assertEqual(latest.to_state, "investigating")

    def test_direct_event_create_blocked(self):
        dispute = self._build_dispute()
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.dispute.event"].create({
                "dispute_id": dispute.id,
                "event_type": "note",
                "summary": "Tampered event",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-DSP-009]", str(ctx.exception))

    def test_event_field_immutable(self):
        dispute = self._build_dispute()
        event = dispute.event_ids[0]
        with self.assertRaises(UserError) as ctx:
            event.write({"summary": "Tampered summary"})
        self.assertIn("[EHL-DSP-010]", str(ctx.exception))
        # Notes is mutable.
        event.write({"notes": "Annotated by ops."})

    def test_event_unlink_blocked(self):
        dispute = self._build_dispute()
        event = dispute.event_ids[0]
        with self.assertRaises(UserError) as ctx:
            event.unlink()
        self.assertIn("[EHL-DSP-011]", str(ctx.exception))
