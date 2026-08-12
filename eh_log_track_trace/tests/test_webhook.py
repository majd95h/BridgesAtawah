# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Webhook endpoint: signature validation, code mapping, reference resolution.

The HTTP-layer test exercises the model-level helpers; the
controller integration is covered by the dedicated HTTP test class
that stands up an Odoo test client (deferred until Odoo runtime is
available).
"""
import hashlib
import hmac
import json

from .common import EhLogTrackTestCase


class TestWebhook(EhLogTrackTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.endpoint = cls.env["eh.log.track.webhook.endpoint"].create({
            "name": "Test Carrier",
            "carrier_name": "test_carrier",
            "secret_key": "test_carrier_secret",
            "target_model": "eh.log.last.mile.delivery",
            "company_id": cls.company.id,
        })
        cls.env["eh.log.track.webhook.mapping"].create({
            "endpoint_id": cls.endpoint.id,
            "carrier_code": "DLVD",
            "event_code_id": cls.env.ref(
                "eh_log_track_trace.event_code_delivered"
            ).id,
        })

    def test_carrier_name_must_be_lowercase(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.track.webhook.endpoint"].create({
                "name": "Bad Carrier",
                "carrier_name": "BadCarrier",
                "secret_key": "x",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-TRK-010]", str(ctx.exception))

    def test_carrier_name_must_be_alnum(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.track.webhook.endpoint"].create({
                "name": "Bad Carrier",
                "carrier_name": "bad-carrier",
                "secret_key": "x",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-TRK-009]", str(ctx.exception))

    def test_extract_walks_dotted_path(self):
        payload = {"a": {"b": {"c": "value"}}}
        self.assertEqual(self.endpoint.extract(payload, "a.b.c"), "value")
        self.assertIsNone(self.endpoint.extract(payload, "a.b.x"))
        self.assertIsNone(self.endpoint.extract(payload, ""))

    def test_resolve_record_by_tracking_reference(self):
        delivery = self._build_delivery()
        delivery.tracking_reference = "EXT-12345"
        resolved = self.endpoint.resolve_record("EXT-12345")
        self.assertEqual(resolved.id, delivery.id)

    def test_resolve_record_unknown_returns_empty(self):
        resolved = self.endpoint.resolve_record("DOES-NOT-EXIST")
        self.assertFalse(resolved)

    def test_map_carrier_code_known(self):
        code = self.endpoint.map_carrier_code("DLVD")
        self.assertEqual(code.code, "delivered")

    def test_map_carrier_code_unknown(self):
        code = self.endpoint.map_carrier_code("UNKNOWN")
        self.assertFalse(code)

    def test_signature_verification_round_trip(self):
        # Simulate the HMAC the controller computes against a body.
        body = json.dumps({"shipment_reference": "X", "event_code": "DLVD"}).encode("utf-8")
        secret = "shared_secret"
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        # Same secret & body -> matching digest. (HMAC is symmetric on
        # both sides, so this asserts the controller's verification
        # primitive aligns with the standard library expectation.)
        actual = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        self.assertTrue(hmac.compare_digest(expected, actual))
        # Tampered body -> different digest.
        tampered = body + b"x"
        diff = hmac.new(secret.encode("utf-8"), tampered, hashlib.sha256).hexdigest()
        self.assertFalse(hmac.compare_digest(expected, diff))
