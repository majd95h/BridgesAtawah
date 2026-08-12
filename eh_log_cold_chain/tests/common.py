# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_cold_chain tests."""
from datetime import datetime, timedelta

from odoo.tests import TransactionCase


class EhLogColdChainTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({
            "name": "Test Cold Chain Customer",
            "is_company": True,
        })
        cls.profile_pharma = cls.env.ref("eh_log_cold_chain.profile_pharma_2_8")
        cls.profile_frozen = cls.env.ref("eh_log_cold_chain.profile_frozen")

        # Build a sale order + freight job to attach runs to.
        cls.order = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "company_id": cls.company.id,
            "eh_log_is_logistics": True,
            "eh_log_mode": "sea",
            "eh_log_direction": "import",
            "eh_log_cold_chain_required": True,
            "eh_log_cold_chain_profile_id": cls.profile_pharma.id,
        })
        cls.env["sale.order.line"].create({
            "order_id": cls.order.id,
            "name": "Reefer freight",
            "product_uom_qty": 1.0,
            "price_unit": 5000.0,
        })
        cls.order.action_confirm()
        cls.order.invalidate_recordset()
        cls.job = cls.order.eh_log_freight_job_ids[:1]

    def _build_run(self, profile=None):
        return self.env["eh.log.cold.chain.run"].create({
            "freight_job_id": self.job.id,
            "profile_id": (profile or self.profile_pharma).id,
            "company_id": self.company.id,
        })

    def _seconds_apart(self, base: datetime, minutes: int) -> datetime:
        return base + timedelta(minutes=minutes)
