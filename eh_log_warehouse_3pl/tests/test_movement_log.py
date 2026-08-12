# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Movement log: append-only, on-hand compute."""
from odoo.exceptions import UserError

from .common import EhLogWarehouseTestCase


class TestMovementLog(EhLogWarehouseTestCase):

    def test_direct_create_blocked(self):
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.warehouse.movement"].create({
                "movement_type": "receipt",
                "client_id": self.client.id,
                "facility_id": self.facility.id,
                "destination_location_id": self.location.id,
                "product_id": self.product.id,
                "quantity": 10.0,
                "pallet_count": 1,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-WHS-014]", str(ctx.exception))

    def test_movement_field_immutable(self):
        receipt = self._build_receipt()
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        movement = self.env["eh.log.warehouse.movement"].search([
            ("receipt_id", "=", receipt.id),
        ], limit=1)
        with self.assertRaises(UserError) as ctx:
            movement.write({"quantity": 999.0})
        self.assertIn("[EHL-WHS-015]", str(ctx.exception))
        # Notes is mutable.
        movement.write({"notes": "Verified manually."})

    def test_movement_unlink_blocked(self):
        receipt = self._build_receipt()
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        movement = self.env["eh.log.warehouse.movement"].search([
            ("receipt_id", "=", receipt.id),
        ], limit=1)
        with self.assertRaises(UserError) as ctx:
            movement.unlink()
        self.assertIn("[EHL-WHS-016]", str(ctx.exception))

    def test_pallets_on_hand_after_receipt_and_pick(self):
        receipt = self._build_receipt(lines=[(self.product, 100, 3, self.location)])
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        self.location.invalidate_recordset()
        self.assertEqual(self.location.pallets_on_hand, 3)

        pick = self._build_pick(lines=[(self.product, 50, 1, self.location)])
        pick.action_start_picking()
        self.location.invalidate_recordset()
        self.assertEqual(self.location.pallets_on_hand, 2)
