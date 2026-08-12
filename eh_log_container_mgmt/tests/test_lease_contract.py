# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Lease contract: term computation, headline value, container assignment."""
from datetime import date

from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogContainerMgmtTestCase


class TestLeaseContract(EhLogContainerMgmtTestCase):

    def setUp(self):
        super().setUp()
        self.contract = self.env["eh.log.container.mgmt.lease.contract"].create({
            "direction": "lease_in",
            "partner_id": self.customer.id,
            "iso_type_id": self.iso_40hc.id,
            "fleet_count": 50,
            "daily_rate": 5.0,
            "starts_on": date(2026, 6, 1),
            "ends_on": date(2026, 6, 30),
        })

    def test_days_total_inclusive(self):
        # 1 June through 30 June inclusive = 30 days
        self.assertEqual(self.contract.days_total, 30)

    def test_headline_value(self):
        # 50 containers * 5/day * 30 days = 7500
        self.assertEqual(self.contract.headline_value, 7500.0)

    def test_term_invariant(self):
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.container.mgmt.lease.contract"].create({
                "direction": "lease_out",
                "partner_id": self.customer.id,
                "iso_type_id": self.iso_40hc.id,
                "fleet_count": 1,
                "daily_rate": 1.0,
                "starts_on": date(2026, 6, 30),
                "ends_on": date(2026, 6, 1),  # before starts_on
            })
        self.assertIn("[EHL-CTNR-LEASE-001]", str(ctx.exception))

    def test_container_assignment_rolls_up_to_count(self):
        self.container.lease_contract_id = self.contract
        self.contract.invalidate_recordset()
        self.assertEqual(self.contract.container_count, 1)

    def test_state_machine(self):
        self.assertEqual(self.contract.state, "draft")
        self.contract.action_activate()
        self.assertEqual(self.contract.state, "active")
        self.contract.action_expire()
        self.assertEqual(self.contract.state, "expired")
        with self.assertRaises(JobStateConflictError):
            self.contract.action_activate()  # not allowed from expired

    def test_direct_state_write_blocked(self):
        with self.assertRaises(UserError) as ctx:
            self.contract.write({"state": "active"})
        self.assertIn("[EHL-CTNR-LEASE-002]", str(ctx.exception))
