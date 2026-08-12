# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Disbursement account: estimate / actual / variance, sale order post."""
from odoo.exceptions import UserError

from .common import EhLogShipTestCase


class TestDisbursementAccount(EhLogShipTestCase):

    def _build_account(self):
        call = self._build_port_call()
        call.action_open_disbursement()
        return call.disbursement_account_id

    def test_initial_state(self):
        account = self._build_account()
        self.assertEqual(account.state, "draft")
        self.assertTrue(account.name.startswith("DA/"))

    def test_estimate_actual_variance(self):
        account = self._build_account()
        Line = self.env["eh.log.ship.disbursement.line"]
        Line.create({
            "account_id": account.id,
            "description": "Port dues estimate",
            "is_estimate": True,
            "amount": 5000.0,
        })
        Line.create({
            "account_id": account.id,
            "description": "Pilotage estimate",
            "is_estimate": True,
            "amount": 1500.0,
        })
        Line.create({
            "account_id": account.id,
            "description": "Port dues actual",
            "is_estimate": False,
            "amount": 5200.0,
        })
        account.invalidate_recordset()
        self.assertEqual(account.estimate_total, 6500.0)
        self.assertEqual(account.actual_total, 5200.0)
        # variance = actual - estimate = 5200 - 6500 = -1300 (under)
        self.assertEqual(account.variance, -1300.0)

    def test_proforma_requires_estimate_lines(self):
        account = self._build_account()
        with self.assertRaises(UserError) as ctx:
            account.action_issue_proforma()
        self.assertIn("[EHL-SHP-012]", str(ctx.exception))

    def test_full_lifecycle_posts_sale_order(self):
        account = self._build_account()
        Line = self.env["eh.log.ship.disbursement.line"]
        Line.create({
            "account_id": account.id,
            "description": "Estimate line",
            "is_estimate": True,
            "amount": 1000.0,
        })
        account.action_issue_proforma()
        Line.create({
            "account_id": account.id,
            "description": "Actual line",
            "is_estimate": False,
            "amount": 1100.0,
        })
        account.action_record_actuals()
        account.action_post()
        self.assertEqual(account.state, "posted")
        self.assertTrue(account.sale_order_id)
        self.assertEqual(
            account.sale_order_id.partner_id, self.principal,
        )

    def test_state_direct_write_blocked(self):
        account = self._build_account()
        with self.assertRaises(UserError) as ctx:
            account.write({"state": "posted"})
        self.assertIn("[EHL-SHP-014]", str(ctx.exception))

    def test_lines_lock_after_post(self):
        account = self._build_account()
        Line = self.env["eh.log.ship.disbursement.line"]
        line = Line.create({
            "account_id": account.id,
            "description": "Estimate",
            "is_estimate": True,
            "amount": 100.0,
        })
        account.action_issue_proforma()
        Line.create({
            "account_id": account.id,
            "description": "Actual",
            "is_estimate": False,
            "amount": 95.0,
        })
        account.action_record_actuals()
        account.action_post()
        with self.assertRaises(UserError) as ctx:
            line.write({"amount": 200.0})
        self.assertIn("[EHL-SHP-015]", str(ctx.exception))

    def test_husbandry_charge_code_propagates(self):
        account = self._build_account()
        husbandry = self.env.ref(
            "eh_log_ship_agency.husbandry_crew_change_transport"
        )
        line = self.env["eh.log.ship.disbursement.line"].new({
            "account_id": account.id,
            "description": "Crew change",
            "is_estimate": False,
            "husbandry_service_id": husbandry.id,
        })
        line._onchange_husbandry_service()
        self.assertEqual(
            line.charge_code_id, husbandry.charge_code_id,
        )
