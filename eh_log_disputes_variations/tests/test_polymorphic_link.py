# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Polymorphic source link: allow-list + existence validation."""
from odoo.exceptions import ValidationError

from .common import EhLogDisputesTestCase


class TestPolymorphicLink(EhLogDisputesTestCase):

    def test_dispute_against_freight_job_works(self):
        job = self._build_freight_job()
        dispute = self._build_dispute(source_record=job)
        self.assertEqual(dispute.res_model, "eh.log.freight.job")
        self.assertEqual(dispute.res_id, job.id)
        self.assertIn(job.name or "", dispute.source_display)

    def test_dispute_against_sale_order_works(self):
        order = self._build_sale_order()
        dispute = self._build_dispute(source_record=order)
        self.assertEqual(dispute.res_model, "sale.order")

    def test_dispute_rejects_non_allowlisted_model(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.dispute"].create({
                "subject": "Bad source",
                "category_id": self.category_damage.id,
                "customer_id": self.customer.id,
                "res_model": "res.partner",
                "res_id": self.customer.id,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-DSP-003]", str(ctx.exception))

    def test_dispute_rejects_unknown_source_id(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.dispute"].create({
                "subject": "Phantom source",
                "category_id": self.category_damage.id,
                "customer_id": self.customer.id,
                "res_model": "eh.log.freight.job",
                "res_id": 999_999_999,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-DSP-004]", str(ctx.exception))

    def test_variation_against_freight_job_resolves_no_sale_order(self):
        job = self._build_freight_job()
        variation = self._build_variation(source_record=job)
        # A freight job created standalone without a sale_order_id
        # results in sale_order_id == False; apply will then refuse.
        self.assertFalse(variation.sale_order_id)

    def test_variation_against_sale_order_resolves_self(self):
        order = self._build_sale_order()
        variation = self._build_variation(source_record=order)
        self.assertEqual(variation.sale_order_id, order)

    def test_variation_rejects_non_allowlisted_model(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.variation"].create({
                "subject": "Bad source",
                "customer_id": self.customer.id,
                "res_model": "res.partner",
                "res_id": self.customer.id,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-VAR-001]", str(ctx.exception))

    def test_sale_order_count_helper_works(self):
        order = self._build_sale_order()
        # Add one dispute and one variation, then read counts.
        self._build_dispute(source_record=order)
        self._build_variation(source_record=order)
        order.invalidate_recordset()
        self.assertEqual(order.eh_log_dispute_count, 1)
        self.assertEqual(order.eh_log_variation_count, 1)

    def test_freight_job_count_helper_works(self):
        job = self._build_freight_job()
        self._build_dispute(source_record=job)
        job.invalidate_recordset()
        self.assertEqual(job.eh_log_dispute_count, 1)
