# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Receipt: state machine, putaway emits movements, lines lock on close."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogWarehouseTestCase


class TestReceiptLifecycle(EhLogWarehouseTestCase):

    def test_initial_state(self):
        receipt = self._build_receipt()
        self.assertEqual(receipt.state, "expected")
        self.assertTrue(receipt.name.startswith("WHR/"))

    def test_full_path(self):
        receipt = self._build_receipt()
        receipt.action_mark_arrived()
        self.assertEqual(receipt.state, "arrived")
        self.assertTrue(receipt.arrived_at)
        receipt.action_start_inspection()
        self.assertEqual(receipt.state, "inspecting")
        receipt.action_complete_putaway()
        self.assertEqual(receipt.state, "putaway")
        self.assertTrue(receipt.putaway_at)
        receipt.action_close()
        self.assertEqual(receipt.state, "closed")

    def test_putaway_blocked_without_destinations(self):
        receipt = self._build_receipt(lines=[
            (self.product, 100, 2, None),
        ])
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        with self.assertRaises(UserError) as ctx:
            receipt.action_complete_putaway()
        self.assertIn("[EHL-WHS-011]", str(ctx.exception))

    def test_putaway_emits_movements(self):
        receipt = self._build_receipt()
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        movements = self.env["eh.log.warehouse.movement"].search([
            ("receipt_id", "=", receipt.id),
        ])
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements.movement_type, "receipt")
        self.assertEqual(movements.pallet_count, 2)

    def test_disallowed_transition_blocked(self):
        receipt = self._build_receipt()
        with self.assertRaises(JobStateConflictError):
            receipt.action_close()  # cannot close from expected

    def test_direct_state_write_blocked(self):
        receipt = self._build_receipt()
        with self.assertRaises(UserError) as ctx:
            receipt.write({"state": "closed"})
        self.assertIn("[EHL-WHS-007]", str(ctx.exception))

    def test_lines_lock_after_close(self):
        receipt = self._build_receipt()
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        receipt.action_close()
        with self.assertRaises(UserError) as ctx:
            receipt.line_ids[0].write({"quantity": 200.0})
        self.assertIn("[EHL-WHS-008]", str(ctx.exception))
