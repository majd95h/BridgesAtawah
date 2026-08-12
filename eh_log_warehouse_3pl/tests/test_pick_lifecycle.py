# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Pick: state machine, picking emits movements."""
from odoo.exceptions import UserError

from .common import EhLogWarehouseTestCase


class TestPickLifecycle(EhLogWarehouseTestCase):

    def test_initial_state(self):
        pick = self._build_pick()
        self.assertEqual(pick.state, "planned")
        self.assertTrue(pick.name.startswith("WHP/"))

    def test_full_path(self):
        pick = self._build_pick()
        pick.action_start_picking()
        self.assertEqual(pick.state, "picking")
        self.assertTrue(pick.picking_started_at)
        pick.action_mark_packed()
        self.assertEqual(pick.state, "packed")
        pick.action_mark_shipped()
        self.assertEqual(pick.state, "shipped")
        self.assertTrue(pick.shipped_at)
        pick.action_close()
        self.assertEqual(pick.state, "closed")

    def test_picking_emits_movements(self):
        pick = self._build_pick()
        pick.action_start_picking()
        movements = self.env["eh.log.warehouse.movement"].search([
            ("pick_id", "=", pick.id),
        ])
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements.movement_type, "pick")

    def test_picking_blocked_without_source(self):
        pick = self._build_pick(lines=[
            (self.product, 50, 1, None),
        ])
        with self.assertRaises(UserError) as ctx:
            pick.action_start_picking()
        self.assertIn("[EHL-WHS-013]", str(ctx.exception))
