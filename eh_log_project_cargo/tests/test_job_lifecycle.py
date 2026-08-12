# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Job state machine: prerequisites for each transition."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogProjectCargoTestCase


class TestJobLifecycle(EhLogProjectCargoTestCase):

    def test_initial_state(self):
        job = self._build_job()
        self.assertEqual(job.state, "draft")
        self.assertTrue(job.name.startswith("PCG/"))

    def test_surveyed_requires_route_survey(self):
        job = self._build_job()
        with self.assertRaises(UserError) as ctx:
            job.action_mark_surveyed()
        self.assertIn("[EHL-PCG-002]", str(ctx.exception))

    def test_surveyed_passes_with_survey(self):
        job = self._build_job()
        self._add_route_survey(job)
        job.action_mark_surveyed()
        self.assertEqual(job.state, "surveyed")

    def test_planned_requires_convoy_with_vehicles(self):
        job = self._build_job()
        self._add_route_survey(job)
        job.action_mark_surveyed()
        with self.assertRaises(UserError) as ctx:
            job.action_mark_planned()
        self.assertIn("[EHL-PCG-003]", str(ctx.exception))

        empty_convoy = self._add_convoy(job, with_vehicles=False)
        with self.assertRaises(UserError) as ctx:
            job.action_mark_planned()
        self.assertIn("[EHL-PCG-004]", str(ctx.exception))

    def test_full_lifecycle(self):
        job = self._build_job()
        self._add_route_survey(job)
        job.action_mark_surveyed()
        self._add_convoy(job)
        job.action_mark_planned()
        # Add issued permit so executing prerequisites pass.
        permit = self._add_permit(job)
        permit.action_apply()
        permit.action_mark_issued()
        permit.action_activate()
        job.action_start_execution()
        self.assertEqual(job.state, "executing")
        job.action_mark_completed()
        self.assertEqual(job.state, "completed")
        job.action_close()
        self.assertEqual(job.state, "closed")

    def test_executing_blocked_with_unissued_permit(self):
        job = self._build_job()
        self._add_route_survey(job)
        job.action_mark_surveyed()
        self._add_convoy(job)
        job.action_mark_planned()
        # Permit in draft state.
        self._add_permit(job)
        with self.assertRaises(UserError) as ctx:
            job.action_start_execution()
        self.assertIn("[EHL-PCG-005]", str(ctx.exception))

    def test_state_direct_write_blocked(self):
        job = self._build_job()
        with self.assertRaises(UserError) as ctx:
            job.write({"state": "executing"})
        self.assertIn("[EHL-PCG-006]", str(ctx.exception))

    def test_disallowed_transition_blocked(self):
        job = self._build_job()
        with self.assertRaises(JobStateConflictError):
            job.action_mark_planned()  # cannot plan from draft
