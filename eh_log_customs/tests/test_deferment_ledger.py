# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Deferment account: balance from entries, low-balance flag, account uniqueness."""
from psycopg2 import IntegrityError
from odoo.tools.misc import mute_logger

from .common import EhLogCustomsTestCase


class TestDefermentLedger(EhLogCustomsTestCase):

    def test_balance_starts_at_opening_balance(self):
        self.assertEqual(self.deferment.current_balance, 50000.0)

    def test_credit_increases_balance(self):
        self.env["eh.log.customs.deferment.entry"].create({
            "account_id": self.deferment.id,
            "entry_kind": "credit",
            "amount": 10000.0,
            "description": "Top-up",
            "state": "posted",
        })
        self.deferment.invalidate_recordset()
        self.assertEqual(self.deferment.current_balance, 60000.0)

    def test_debit_reduces_balance(self):
        self.env["eh.log.customs.deferment.entry"].create({
            "account_id": self.deferment.id,
            "entry_kind": "debit",
            "amount": 8000.0,
            "description": "Duty payment",
            "state": "posted",
        })
        self.deferment.invalidate_recordset()
        self.assertEqual(self.deferment.current_balance, 42000.0)

    def test_cancelled_entries_do_not_count(self):
        self.env["eh.log.customs.deferment.entry"].create({
            "account_id": self.deferment.id,
            "entry_kind": "credit",
            "amount": 10000.0,
            "description": "Cancelled top-up",
            "state": "cancelled",
        })
        self.deferment.invalidate_recordset()
        self.assertEqual(self.deferment.current_balance, 50000.0)

    def test_low_balance_flag(self):
        self.deferment.low_balance_threshold = 100000.0
        self.deferment.invalidate_recordset()
        self.assertTrue(self.deferment.is_low)
        self.deferment.low_balance_threshold = 1000.0
        self.deferment.invalidate_recordset()
        self.assertFalse(self.deferment.is_low)

    def test_account_unique_per_company_and_regulator(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["eh.log.customs.deferment.account"].create({
                    "name": "Duplicate",
                    "account_number": "TEST-001",
                    "regulator_profile_id": self.regulator_profile.id,
                    "company_id": self.company.id,
                    "currency_id": self.env.company.currency_id.id,
                })
