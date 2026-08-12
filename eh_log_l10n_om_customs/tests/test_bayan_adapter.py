# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Bayan (Oman) adapter: registry, serialise, parse, mock-mode round trip."""
import json

from odoo.tests import TransactionCase

from odoo.addons.eh_log_base import adapter_registry
from odoo.addons.eh_log_l10n_om_customs.adapters.bayan import BayanAdapter


SAMPLE_PAYLOAD = {
    "broker_reference": "BRK-OM-001",
    "declaration_type": "OM-IMP",
    "declaration_date": "2026-06-01",
    "currency": "OMR",
    "customs_value": 5000.00,
    "duty_amount": 250.00,
    "vat_amount": 262.50,
    "payable_amount": 512.50,
    "importer": {"name": "Acme Oman Imports LLC", "vat": "OM1100000000"},
    "exporter": {"name": "Beta Exporter Ltd", "vat": ""},
    "lines": [
        {
            "hs_code": "851712",
            "description": "Smartphones",
            "country_of_origin": "CN",
            "quantity": 50,
            "unit_value": 100.00,
            "customs_value": 5000.00,
            "duty_rate_pct": 5.00,
            "vat_rate_pct": 5.00,
            "duty_amount": 250.00,
            "vat_amount": 262.50,
        },
    ],
}


class TestBayanAdapterRegistry(TransactionCase):

    def test_adapter_registered_at_import(self):
        cls = adapter_registry.get("bayan")
        self.assertIs(cls, BayanAdapter)

    def test_default_profile_seeded(self):
        profile = self.env.ref("eh_log_l10n_om_customs.profile_bayan_default")
        self.assertEqual(profile.provider_code, "bayan")
        self.assertEqual(profile.environment, "mock")


class TestBayanAdapterSerialise(TransactionCase):

    def setUp(self):
        super().setUp()
        self.profile = self.env.ref("eh_log_l10n_om_customs.profile_bayan_default")
        self.adapter = BayanAdapter(self.profile)

    def test_serialize_produces_valid_json(self):
        raw = self.adapter.serialize("declaration_submit", SAMPLE_PAYLOAD)
        parsed = json.loads(raw)
        self.assertEqual(parsed["brokerReference"], "BRK-OM-001")
        self.assertEqual(parsed["totals"]["payableAmount"], 512.50)


class TestBayanAdapterParse(TransactionCase):

    def setUp(self):
        super().setUp()
        self.profile = self.env.ref("eh_log_l10n_om_customs.profile_bayan_default")
        self.adapter = BayanAdapter(self.profile)

    def test_parse_success(self):
        from pathlib import Path
        fixture = Path(__file__).parent / "fixtures" / "bayan" / "declaration_submit.success.json"
        parsed = self.adapter.parse("declaration_submit", fixture.read_text(encoding="utf-8"))
        self.assertEqual(parsed["regulator_reference"], "BAY-2026-567890123")
        self.assertEqual(parsed["status"], "ACCEPTED")

    def test_parse_rejection(self):
        from pathlib import Path
        fixture = Path(__file__).parent / "fixtures" / "bayan" / "declaration_submit.rejected.json"
        parsed = self.adapter.parse("declaration_submit", fixture.read_text(encoding="utf-8"))
        self.assertEqual(parsed["status"], "REJECTED")
        self.assertEqual(parsed["errors"][0]["code"], "VAT_REGISTRATION_REQUIRED")


class TestBayanAdapterMockRoundTrip(TransactionCase):

    def test_mock_call_round_trip(self):
        profile = self.env.ref("eh_log_l10n_om_customs.profile_bayan_default")
        adapter = BayanAdapter(profile)
        result = adapter.call(
            message_type="declaration_submit",
            payload=SAMPLE_PAYLOAD,
            related_model="eh.log.customs.declaration",
            related_record_id=1,
            related_record_display="TEST",
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.parsed["regulator_reference"], "BAY-2026-567890123")
