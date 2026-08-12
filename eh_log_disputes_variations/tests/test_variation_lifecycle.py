# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Variation: state machine, line lock, apply pushes to sale order."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogDisputesTestCase


class TestVariationLifecycle(EhLogDisputesTestCase):

    def test_initial_state(self):
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order)
        self.assertEqual(variation.state, "draft")
        self.assertTrue(variation.name.startswith("VAR/"))
        self.assertEqual(variation.sale_order_id, order)

    def test_full_lifecycle_apply_creates_so_lines(self):
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order, lines=[
            ("Re-routing fee", 1.0, 500.0),
            ("Additional handling", 2.0, 100.0),
        ])
        self.assertEqual(variation.net_amount, 700.0)
        variation.action_submit()
        self.assertEqual(variation.state, "submitted")
        self.assertTrue(variation.submitted_at)
        variation.action_approve()
        self.assertEqual(variation.state, "approved")
        self.assertTrue(variation.approved_at)
        before_lines = len(order.order_line)
        variation.action_apply()
        self.assertEqual(variation.state, "applied")
        self.assertTrue(variation.applied_at)
        # Two new SO lines should appear.
        order.invalidate_recordset()
        self.assertEqual(len(order.order_line), before_lines + 2)
        self.assertEqual(len(variation.applied_line_ids), 2)
        # Reference text on the SO lines carries the variation ref.
        for line in variation.applied_line_ids:
            self.assertIn(variation.name, line.name)

    def test_submit_requires_lines(self):
        order = self._build_sale_order()
        variation = self.env["eh.log.variation"].create({
            "subject": "Empty variation",
            "customer_id": self.customer.id,
            "res_model": "sale.order",
            "res_id": order.id,
            "company_id": self.company.id,
        })
        with self.assertRaises(UserError) as ctx:
            variation.action_submit()
        self.assertIn("[EHL-VAR-003]", str(ctx.exception))

    def test_apply_requires_sale_order(self):
        # Source is a freight job without a sale order link.
        job = self._build_freight_job()
        variation = self._build_variation(source_record=job)
        variation.action_submit()
        variation.action_approve()
        with self.assertRaises(UserError) as ctx:
            variation.action_apply()
        self.assertIn("[EHL-VAR-004]", str(ctx.exception))

    def test_lines_lock_after_approval(self):
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order)
        variation.action_submit()
        variation.action_approve()
        line = variation.line_ids[0]
        with self.assertRaises(UserError) as ctx:
            line.write({"unit_price": 999.0})
        self.assertIn("[EHL-VAR-006]", str(ctx.exception))

    def test_state_direct_write_blocked(self):
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order)
        with self.assertRaises(UserError) as ctx:
            variation.write({"state": "approved"})
        self.assertIn("[EHL-VAR-005]", str(ctx.exception))

    def test_disallowed_transition(self):
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order)
        with self.assertRaises(JobStateConflictError):
            variation.action_apply()  # cannot apply from draft

    def test_negative_unit_price_for_credit(self):
        # Negative unit price represents a charge reduction; the
        # net amount becomes negative and applies to the SO as a
        # credit line.
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order, lines=[
            ("Goodwill credit", 1.0, -200.0),
        ])
        self.assertEqual(variation.net_amount, -200.0)
        variation.action_submit()
        variation.action_approve()
        variation.action_apply()
        applied = variation.applied_line_ids[0]
        self.assertEqual(applied.price_unit, -200.0)
