# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Work order: state machine, line gating, manager-only approval."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogContainerMgmtTestCase


class TestWorkOrder(EhLogContainerMgmtTestCase):

    def setUp(self):
        super().setUp()
        self.wo = self.env["eh.log.container.mgmt.work.order"].create({
            "container_id": self.container.id,
            "depot_id": self.depot_origin.id,
            "fault_description": "Side panel dented during stevedore handling.",
        })

    def test_initial_state(self):
        self.assertEqual(self.wo.state, "draft")
        self.assertTrue(self.wo.name.startswith("WO/"))

    def test_estimate_blocked_without_lines(self):
        with self.assertRaises(UserError) as ctx:
            self.wo.action_set_estimated()
        self.assertIn("[EHL-CTNR-WO-002]", str(ctx.exception))

    def test_full_lifecycle_with_costs(self):
        line = self.env["eh.log.container.mgmt.work.order.line"].create({
            "work_order_id": self.wo.id,
            "repair_kind": "dent",
            "description": "Hammer + repaint side panel",
            "quantity": 1,
            "estimated_unit_cost": 200.0,
        })
        self.wo.invalidate_recordset()
        self.assertEqual(self.wo.estimated_cost, 200.0)
        self.wo.action_set_estimated()
        self.assertEqual(self.wo.state, "estimated")
        # Approve (admin is in manager group via base post_init_hook).
        self.wo.action_approve()
        self.assertEqual(self.wo.state, "approved")
        self.wo.action_start()
        self.assertEqual(self.wo.state, "in_progress")
        # Cannot complete without actual costs.
        with self.assertRaises(UserError) as ctx:
            self.wo.action_complete()
        self.assertIn("[EHL-CTNR-WO-004]", str(ctx.exception))
        line.actual_unit_cost = 220.0
        self.wo.invalidate_recordset()
        self.assertEqual(self.wo.actual_cost, 220.0)
        self.wo.action_complete()
        self.assertEqual(self.wo.state, "completed")
        self.wo.action_close()
        self.assertEqual(self.wo.state, "closed")

    def test_disallowed_transition_blocked(self):
        with self.assertRaises(JobStateConflictError):
            self.wo.action_complete()

    def test_direct_state_write_blocked(self):
        with self.assertRaises(UserError) as ctx:
            self.wo.write({"state": "approved"})
        self.assertIn("[EHL-CTNR-WO-001]", str(ctx.exception))
