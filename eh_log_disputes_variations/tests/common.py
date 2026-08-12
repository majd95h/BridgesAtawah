# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_disputes_variations tests."""
from odoo.tests import TransactionCase


class EhLogDisputesTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({
            "name": "Dispute Test Customer",
            "is_company": True,
        })
        cls.shipper = cls.env["res.partner"].create({
            "name": "Dispute Test Shipper",
            "is_company": True,
        })
        cls.consignee = cls.env["res.partner"].create({
            "name": "Dispute Test Consignee",
            "is_company": True,
        })
        cls.category_damage = cls.env.ref(
            "eh_log_disputes_variations.category_cargo_damage"
        )
        cls.category_pricing = cls.env.ref(
            "eh_log_disputes_variations.category_pricing"
        )

    def _build_freight_job(self):
        return self.env["eh.log.freight.job"].create({
            "customer_id": self.customer.id,
            "shipper_id": self.shipper.id,
            "consignee_id": self.consignee.id,
            "company_id": self.company.id,
        })

    def _build_sale_order(self):
        return self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "company_id": self.company.id,
        })

    def _build_dispute(self, source_record=None, category=None,
                       claimed=1000.0):
        source = source_record or self._build_freight_job()
        return self.env["eh.log.dispute"].create({
            "subject": "Test dispute subject",
            "category_id": (category or self.category_damage).id,
            "customer_id": self.customer.id,
            "res_model": source._name,
            "res_id": source.id,
            "claimed_amount": claimed,
            "company_id": self.company.id,
        })

    def _build_variation(self, source_record=None, lines=None):
        source = source_record or self._build_sale_order()
        variation = self.env["eh.log.variation"].create({
            "subject": "Add additional handling",
            "customer_id": self.customer.id,
            "res_model": source._name,
            "res_id": source.id,
            "company_id": self.company.id,
        })
        for description, qty, price in (lines or [
            ("Additional handling fee", 1.0, 250.0),
        ]):
            self.env["eh.log.variation.line"].create({
                "variation_id": variation.id,
                "description": description,
                "quantity": qty,
                "unit_price": price,
            })
        return variation
