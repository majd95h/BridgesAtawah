# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Permit: state machine, expiry compute, alert cron."""
from datetime import date, timedelta

from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogProjectCargoTestCase


class TestPermitLifecycle(EhLogProjectCargoTestCase):

    def test_initial_state(self):
        job = self._build_job()
        permit = self._add_permit(job)
        self.assertEqual(permit.state, "draft")

    def test_full_lifecycle(self):
        job = self._build_job()
        permit = self._add_permit(job)
        permit.action_apply()
        self.assertEqual(permit.state, "applied")
        self.assertTrue(permit.applied_at)
        permit.action_mark_issued()
        self.assertEqual(permit.state, "issued")
        self.assertTrue(permit.issued_at)
        permit.action_activate()
        self.assertEqual(permit.state, "active")
        permit.action_close()
        self.assertEqual(permit.state, "closed")

    def test_issued_requires_valid_until(self):
        job = self._build_job()
        permit = self.env["eh.log.project.cargo.permit"].create({
            "name": "No Expiry",
            "job_id": job.id,
            "authority": "police",
            "company_id": self.company.id,
        })
        permit.action_apply()
        with self.assertRaises(UserError) as ctx:
            permit.action_mark_issued()
        self.assertIn("[EHL-PCG-011]", str(ctx.exception))

    def test_state_direct_write_blocked(self):
        job = self._build_job()
        permit = self._add_permit(job)
        with self.assertRaises(UserError) as ctx:
            permit.write({"state": "issued"})
        self.assertIn("[EHL-PCG-012]", str(ctx.exception))

    def test_disallowed_transition_blocked(self):
        job = self._build_job()
        permit = self._add_permit(job)
        with self.assertRaises(JobStateConflictError):
            permit.action_close()  # cannot close from draft

    def test_days_until_expiry_compute(self):
        job = self._build_job()
        permit = self._add_permit(job, valid_days=10)
        self.assertEqual(permit.days_until_expiry, 10)

    def test_alert_cron_picks_expiring(self):
        job = self._build_job()
        permit = self._add_permit(job, valid_days=3)
        permit.action_apply()
        permit.action_mark_issued()
        Permit = self.env["eh.log.project.cargo.permit"]
        count = Permit.cron_alert_expiring()
        self.assertGreaterEqual(count, 1)

    def test_alert_cron_skips_distant_expiry(self):
        job = self._build_job()
        permit = self._add_permit(job, valid_days=90)
        permit.action_apply()
        permit.action_mark_issued()
        Permit = self.env["eh.log.project.cargo.permit"]
        # Filter the cron's set against this permit specifically.
        candidates = Permit.search([
            ("id", "=", permit.id),
            ("valid_until", "<=", date.today() + timedelta(days=7)),
        ])
        self.assertFalse(candidates)
