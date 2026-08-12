# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Port call: state machine, NOR tendering, berth compatibility on assign."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogShipTestCase, TEST_IMO_ALT


class TestPortCallLifecycle(EhLogShipTestCase):

    def test_initial_state(self):
        call = self._build_port_call()
        self.assertEqual(call.state, "expected")
        self.assertTrue(call.name.startswith("PCL/"))

    def test_full_path(self):
        call = self._build_port_call()
        call.action_mark_arrived()
        self.assertEqual(call.state, "arrived")
        self.assertTrue(call.arrived_at)
        call.action_assign_berth()
        self.assertEqual(call.state, "berthed")
        self.assertTrue(call.berthed_at)
        call.action_start_working()
        self.assertEqual(call.state, "working")
        call.action_mark_sailed()
        self.assertEqual(call.state, "sailed")
        call.action_close()
        self.assertEqual(call.state, "closed")

    def test_disallowed_transition_blocked(self):
        call = self._build_port_call()
        with self.assertRaises(JobStateConflictError):
            call.action_close()

    def test_state_direct_write_blocked(self):
        call = self._build_port_call()
        with self.assertRaises(UserError) as ctx:
            call.write({"state": "berthed"})
        self.assertIn("[EHL-SHP-009]", str(ctx.exception))

    def test_nor_only_between_arrived_and_berthed(self):
        call = self._build_port_call()
        with self.assertRaises(UserError) as ctx:
            call.action_tender_nor()  # state == expected
        self.assertIn("[EHL-SHP-008]", str(ctx.exception))
        call.action_mark_arrived()
        call.action_tender_nor()
        self.assertTrue(call.nor_tendered_at)

    def test_berth_assignment_rejects_incompatible(self):
        bad_vessel = self.env["eh.log.ship.vessel"].create({
            "name": "Bad Fit",
            "imo_number": TEST_IMO_ALT,
            "vessel_type": "container",
            "draft_m": 18.0,
            "company_id": self.company.id,
        })
        call = self._build_port_call(vessel=bad_vessel)
        call.action_mark_arrived()
        with self.assertRaises(UserError) as ctx:
            call.action_assign_berth()
        self.assertIn("[EHL-SHP-006]", str(ctx.exception))

    def test_state_transition_emits_sof_event(self):
        call = self._build_port_call()
        before = len(call.sof_event_ids)
        call.action_mark_arrived()
        call.invalidate_recordset()
        self.assertGreater(len(call.sof_event_ids), before)

    def test_close_blocked_with_open_disbursement(self):
        call = self._build_port_call()
        call.action_mark_arrived()
        call.action_assign_berth()
        call.action_start_working()
        call.action_mark_sailed()
        # Spawn a disbursement and leave it in draft.
        call.action_open_disbursement()
        with self.assertRaises(UserError) as ctx:
            call.action_close()
        self.assertIn("[EHL-SHP-007]", str(ctx.exception))
