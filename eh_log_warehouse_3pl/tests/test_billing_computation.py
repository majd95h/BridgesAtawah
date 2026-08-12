# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Billing run: handling charges, storage charges, monthly minimum, post."""
from datetime import date

from odoo.exceptions import UserError

from .common import EhLogWarehouseTestCase


class TestBillingComputation(EhLogWarehouseTestCase):

    def _make_run(self):
        return self.env["eh.log.warehouse.billing.run"].create({
            "client_id": self.client.id,
            "rate_card_id": self.rate_card.id,
            "period_start": date.today().replace(day=1),
            "period_end": date.today(),
            "company_id": self.company.id,
        })

    def test_handling_in_charge_appears(self):
        receipt = self._build_receipt(lines=[(self.product, 100, 4, self.location)])
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        run = self._make_run()
        run.action_compute()
        line = run.line_ids.filtered(
            lambda l: l.service_type == "handling_in"
        )
        self.assertTrue(line)
        self.assertEqual(line.quantity, 4.0)
        self.assertEqual(line.unit_price, 5.0)
        self.assertEqual(line.subtotal, 20.0)

    def test_handling_out_charge_appears(self):
        receipt = self._build_receipt(lines=[(self.product, 100, 4, self.location)])
        receipt.action_mark_arrived()
        receipt.action_start_inspection()
        receipt.action_complete_putaway()
        pick = self._build_pick(lines=[(self.product, 50, 2, self.location)])
        pick.action_start_picking()
        run = self._make_run()
        run.action_compute()
        line = run.line_ids.filtered(
            lambda l: l.service_type == "handling_out"
        )
        self.assertTrue(line)
        self.assertEqual(line.quantity, 2.0)
        self.assertEqual(line.subtotal, 12.0)

    def test_monthly_minimum_top_up(self):
        # No movements -> bill should still hit the minimum.
        run = self._make_run()
        run.action_compute()
        line = run.line_ids.filtered(
            lambda l: l.service_type == "monthly_minimum"
        )
        self.assertTrue(line)
        self.assertEqual(line.quantity, 1.0)
        self.assertEqual(line.unit_price, 50.0)

    def test_post_creates_sale_order(self):
        run = self._make_run()
        run.action_compute()
        run.action_post()
        self.assertEqual(run.state, "posted")
        self.assertTrue(run.sale_order_id)
        self.assertEqual(run.sale_order_id.partner_id, self.partner)
        self.assertEqual(
            run.sale_order_id.eh_log_warehouse_billing_run_id,
            run,
        )

    def test_billing_line_direct_create_blocked(self):
        run = self._make_run()
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.warehouse.billing.line"].create({
                "run_id": run.id,
                "service_type": "handling_in",
                "quantity": 1.0,
                "unit_price": 1.0,
                "currency_id": self.rate_card.currency_id.id,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-WHS-023]", str(ctx.exception))

    def test_period_validation(self):
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.warehouse.billing.run"].create({
                "client_id": self.client.id,
                "rate_card_id": self.rate_card.id,
                "period_start": date(2026, 3, 31),
                "period_end": date(2026, 3, 1),
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-WHS-020]", str(ctx.exception))
