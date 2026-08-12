# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Customs declaration: state machine, preflight checks, totals."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import (
    ConfigurationMissingError,
    CustomsDeclarationError,
    JobStateConflictError,
)

from .common import EhLogCustomsTestCase


class TestDeclarationLifecycle(EhLogCustomsTestCase):

    def setUp(self):
        super().setUp()
        self.declaration = self.env["eh.log.customs.declaration"].create({
            "declaration_type_id": self.dt_import.id,
            "regulator_profile_id": self.regulator_profile.id,
            "customer_id": self.customer.id,
            "importer_id": self.importer.id,
            "exporter_id": self.exporter.id,
            "deferment_account_id": self.deferment.id,
            "company_id": self.company.id,
        })

    def _add_line(self, customs_value=10000.0, duty=5.0, vat=5.0):
        return self.env["eh.log.customs.declaration.line"].create({
            "declaration_id": self.declaration.id,
            "hs_code_id": self.hs_8517.id,
            "description": "Test goods",
            "quantity": 1.0,
            "unit_value": customs_value,
            "duty_rate_pct": duty,
            "vat_rate_pct": vat,
        })

    def test_initial_state(self):
        self.assertEqual(self.declaration.state, "draft")
        self.assertTrue(self.declaration.name.startswith("CD/"))

    def test_ready_blocks_when_no_lines(self):
        with self.assertRaises(CustomsDeclarationError) as ctx:
            self.declaration.action_set_ready()
        self.assertIn("[EHL-CUSTOMS-010]", str(ctx.exception))
        self.assertIn("has no HS lines", str(ctx.exception))

    def test_totals_computed_correctly(self):
        # Two lines: 10000 * 5% duty = 500, then VAT 5% on 10500 = 525
        self._add_line(customs_value=10000.0, duty=5.0, vat=5.0)
        self._add_line(customs_value=2000.0, duty=10.0, vat=5.0)
        self.declaration.invalidate_recordset()
        self.assertAlmostEqual(self.declaration.customs_value, 12000.0, places=2)
        self.assertAlmostEqual(self.declaration.duty_amount, 700.0, places=2)
        # VAT line 1: (10000+500)*5% = 525; line 2: (2000+200)*5% = 110; total 635
        self.assertAlmostEqual(self.declaration.vat_amount, 635.0, places=2)
        self.assertAlmostEqual(self.declaration.payable_amount, 1335.0, places=2)

    def test_ready_then_submit_then_assess_then_pay(self):
        self._add_line(customs_value=10000.0, duty=5.0, vat=5.0)
        self.declaration.action_set_ready()
        self.assertEqual(self.declaration.state, "ready")

        # Submit needs adapter; we have no concrete adapter registered
        # for "test_customs_regulator", so the submit raises a clean
        # ConfigurationMissingError.
        with self.assertRaises(ConfigurationMissingError) as ctx:
            self.declaration.action_submit()
        self.assertIn("[EHL-CONFIG-020]", str(ctx.exception))
        self.assertIn("test_customs_regulator", str(ctx.exception))

    def test_pay_debits_deferment(self):
        # Walk into 'paid' bypassing submit by using internal write context
        self._add_line(customs_value=10000.0, duty=5.0, vat=5.0)
        self.declaration.action_set_ready()
        # Force into assessed for the test (manual path).
        self.declaration.with_context(eh_log_customs_internal_state_write=True).write({
            "state": "assessed",
            "assessed_at": "2026-06-01 10:00:00",
        })
        opening = self.deferment.current_balance
        self.declaration.action_pay()
        self.deferment.invalidate_recordset()
        expected = opening - self.declaration.payable_amount
        self.assertAlmostEqual(self.deferment.current_balance, expected, places=2)
        self.assertEqual(self.declaration.state, "paid")

    def test_disallowed_transition_blocked(self):
        self._add_line()
        with self.assertRaises(JobStateConflictError):
            self.declaration.action_set_cleared()

    def test_direct_state_write_blocked(self):
        with self.assertRaises(UserError) as ctx:
            self.declaration.write({"state": "ready"})
        self.assertIn("[EHL-CUSTOMS-DECL-001]", str(ctx.exception))

    def test_audit_event_on_transition(self):
        self._add_line()
        before = self.env["eh.log.event"].search_count([
            ("category", "=", "state_transition"),
            ("related_model", "=", "eh.log.customs.declaration"),
            ("related_record_id", "=", self.declaration.id),
        ])
        self.declaration.action_set_ready()
        after = self.env["eh.log.event"].search_count([
            ("category", "=", "state_transition"),
            ("related_model", "=", "eh.log.customs.declaration"),
            ("related_record_id", "=", self.declaration.id),
        ])
        self.assertEqual(after - before, 1)
