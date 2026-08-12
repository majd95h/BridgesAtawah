# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Convoy: schedule, vehicle compute flags, inspection guard."""
from datetime import date, datetime, timedelta

from odoo.exceptions import UserError, ValidationError

from .common import EhLogProjectCargoTestCase


class TestConvoyAssembly(EhLogProjectCargoTestCase):

    def test_lifting_and_escort_compute_flags(self):
        job = self._build_job()
        convoy = self._add_convoy(job)
        convoy.invalidate_recordset()
        # SPMT alone does not count as lifting; we added crawler at
        # setup but not to the convoy.
        self.assertFalse(convoy.has_lifting_equipment)
        self.assertTrue(convoy.has_escort_vehicle)
        self.env["eh.log.project.cargo.convoy.vehicle"].create({
            "convoy_id": convoy.id,
            "equipment_id": self.crane.id,
            "role": "crane",
        })
        convoy.invalidate_recordset()
        self.assertTrue(convoy.has_lifting_equipment)

    def test_schedule_order_validated(self):
        job = self._build_job()
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.project.cargo.convoy"].create({
                "job_id": job.id,
                "scheduled_departure": datetime.now() + timedelta(days=2),
                "scheduled_arrival": datetime.now() + timedelta(days=1),
            })
        self.assertIn("[EHL-PCG-008]", str(ctx.exception))

    def test_in_transit_requires_vehicle(self):
        job = self._build_job()
        empty_convoy = self._add_convoy(job, with_vehicles=False)
        with self.assertRaises(UserError) as ctx:
            empty_convoy.action_mark_in_transit()
        self.assertIn("[EHL-PCG-009]", str(ctx.exception))

    def test_overdue_inspection_blocks_assignment(self):
        # Set the SPMT inspection date to the past.
        self.spmt.next_inspection_date = date.today() - timedelta(days=5)
        job = self._build_job()
        convoy = self.env["eh.log.project.cargo.convoy"].create({
            "job_id": job.id,
        })
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.project.cargo.convoy.vehicle"].create({
                "convoy_id": convoy.id,
                "equipment_id": self.spmt.id,
                "role": "primary",
            })
        self.assertIn("[EHL-PCG-010]", str(ctx.exception))

    def test_lifecycle_stamps_actuals(self):
        job = self._build_job()
        convoy = self._add_convoy(job)
        convoy.action_mark_in_transit()
        self.assertEqual(convoy.state, "in_transit")
        self.assertTrue(convoy.actual_departure)
        convoy.action_mark_arrived()
        self.assertEqual(convoy.state, "arrived")
        self.assertTrue(convoy.actual_arrival)
