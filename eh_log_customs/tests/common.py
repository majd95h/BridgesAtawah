# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_customs tests."""
from odoo.tests import TransactionCase


class EhLogCustomsTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({
            "name": "Test Customs Customer",
            "is_company": True,
        })
        cls.importer = cls.env["res.partner"].create({
            "name": "Test Importer",
            "is_company": True,
        })
        cls.exporter = cls.env["res.partner"].create({
            "name": "Test Exporter",
            "is_company": True,
        })
        cls.dt_import = cls.env.ref("eh_log_customs.dt_import")
        cls.dt_export = cls.env.ref("eh_log_customs.dt_export")
        cls.hs_8517 = cls.env.ref("eh_log_customs.hs_ch_85")

        cls.regulator_profile = cls.env["eh.log.adapter.profile"].create({
            "name": "Test Customs Regulator (Mock)",
            "provider_code": "test_customs_regulator",
            "provider_kind": "regulator",
            "environment": "mock",
            "api_version": "1.0",
            "auth_method": "api_key",
            "credential_purpose": "test.api_key",
            "endpoint_url": "https://customs.example/v1",
            "company_id": cls.company.id,
        })

        cls.deferment = cls.env["eh.log.customs.deferment.account"].create({
            "name": "Test Customs Deferment, Mock Authority, USD",
            "account_number": "TEST-001",
            "regulator_profile_id": cls.regulator_profile.id,
            "company_id": cls.company.id,
            "currency_id": cls.env.company.currency_id.id,
            "opening_balance": 50000.0,
        })
