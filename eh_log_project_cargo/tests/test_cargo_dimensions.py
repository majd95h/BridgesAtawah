# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Item dimensions: oversized auto-flag, negative-value rejection."""
from odoo.exceptions import ValidationError

from .common import EhLogProjectCargoTestCase


class TestCargoDimensions(EhLogProjectCargoTestCase):

    def test_oversized_auto_flag_on_length(self):
        job = self._build_job()
        item = self.env["eh.log.project.cargo.item"].create({
            "job_id": job.id,
            "name": "Long Beam",
            "length_m": 22.0,
            "width_m": 2.4,
            "height_m": 3.0,
            "weight_t": 30.0,
        })
        self.assertTrue(item.is_oversized)

    def test_oversized_auto_flag_on_weight(self):
        job = self._build_job()
        item = self.env["eh.log.project.cargo.item"].create({
            "job_id": job.id,
            "name": "Heavy Block",
            "length_m": 5.0,
            "width_m": 2.0,
            "height_m": 2.0,
            "weight_t": 80.0,
        })
        self.assertTrue(item.is_oversized)

    def test_within_envelope_not_flagged(self):
        job = self._build_job()
        item = self.env["eh.log.project.cargo.item"].create({
            "job_id": job.id,
            "name": "Pallet of Steel",
            "length_m": 1.2,
            "width_m": 0.8,
            "height_m": 1.5,
            "weight_t": 1.5,
        })
        self.assertFalse(item.is_oversized)

    def test_negative_dimension_rejected(self):
        job = self._build_job()
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.project.cargo.item"].create({
                "job_id": job.id,
                "name": "Bad",
                "length_m": -1.0,
            })
        self.assertIn("[EHL-PCG-007]", str(ctx.exception))

    def test_job_has_oversized_item_aggregate(self):
        job = self._build_job()
        self.assertFalse(job.has_oversized_item)
        self._add_oversized_item(job)
        job.invalidate_recordset()
        self.assertTrue(job.has_oversized_item)

    def test_one_chosen_route_per_job(self):
        job = self._build_job()
        self._add_route_survey(job, chosen=True)
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.project.cargo.route.survey"].create({
                "job_id": job.id,
                "name": "Second Chosen Route",
                "is_chosen_route": True,
            })
        self.assertIn("[EHL-PCG-013]", str(ctx.exception))
