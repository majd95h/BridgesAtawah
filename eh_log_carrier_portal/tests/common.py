# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_carrier_portal tests."""
from datetime import date

from odoo.tests import TransactionCase


class EhLogCarrierTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.country_ae = cls.env.ref("base.ae")
        cls.country_in = cls.env.ref("base.in")
        cls.ocean = cls.env["eh.log.carrier.profile"].create({
            "name": "Mock Ocean Carrier",
            "code": "MOCEAN",
            "mode": "ocean",
            "provider_code": "mock_ocean",
            "api_version": "1.0",
            "credentials_key": "mock_ocean.api_key",
            "is_mock": True,
            "company_id": cls.company.id,
        })
        cls.air = cls.env["eh.log.carrier.profile"].create({
            "name": "Mock Air Carrier",
            "code": "MAIR",
            "mode": "air",
            "provider_code": "mock_air",
            "api_version": "1.0",
            "credentials_key": "mock_air.api_key",
            "is_mock": True,
            "company_id": cls.company.id,
        })

    def _build_request(self, mode="ocean", weight=1000.0, volume=10.0):
        return self.env["eh.log.carrier.rate.request"].create({
            "mode": mode,
            "origin_country_id": self.country_in.id,
            "origin_location_code": "INMUN",
            "destination_country_id": self.country_ae.id,
            "destination_location_code": "AEJEA",
            "ready_by_date": date.today(),
            "weight_kg": weight,
            "volume_cbm": volume,
            "package_count": 5,
            "company_id": self.company.id,
        })
