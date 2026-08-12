# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Movement: append-only, current depot update, repair auto-spawn."""
from datetime import datetime

from odoo.exceptions import UserError

from .common import EhLogContainerMgmtTestCase


class TestMovement(EhLogContainerMgmtTestCase):

    def test_movement_carries_sequence_reference(self):
        mov = self._make_movement("gate_in")
        self.assertTrue(mov.name.startswith("CMV/"))

    def test_movement_updates_container_current_depot(self):
        mov = self._make_movement(
            "gate_in", depot=self.depot_origin,
            when=datetime(2026, 6, 1, 8, 0),
        )
        self.container.invalidate_recordset()
        self.assertEqual(self.container.current_depot_id, self.depot_origin)
        # The gate-out happens after the gate-in, so it becomes the
        # latest movement and drives the current depot.
        self._make_movement("gate_out", depot=self.depot_destination, when=datetime(2026, 6, 5, 12, 0))
        self.container.invalidate_recordset()
        self.assertEqual(self.container.current_depot_id, self.depot_destination)

    def test_repair_flag_spawns_work_order(self):
        WorkOrder = self.env["eh.log.container.mgmt.work.order"]
        before = WorkOrder.search_count([("container_id", "=", self.container.id)])
        self._make_movement(
            "gate_in",
            needs_repair=True,
            condition_note="Dent on left door, paint scuffed.",
        )
        after = WorkOrder.search_count([("container_id", "=", self.container.id)])
        self.assertEqual(after - before, 1)
        wo = WorkOrder.search([("container_id", "=", self.container.id)], limit=1)
        self.assertEqual(wo.state, "draft")
        self.assertIn("Dent", wo.fault_description)

    def test_movement_immutable_after_create(self):
        mov = self._make_movement("gate_in")
        with self.assertRaises(UserError) as ctx:
            mov.write({"happened_at": datetime(2026, 1, 1, 0, 0)})
        self.assertIn("[EHL-CTNR-MOV-001]", str(ctx.exception))
        # condition_note + gate_operator_name are mutable; should not raise.
        mov.write({
            "condition_note": "Updated condition note.",
            "gate_operator_name": "Mr. Smith",
        })
