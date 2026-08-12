# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""IFTMIN translator: payload structure, partner identifier insertion."""
from .common import EhLogEdiTestCase


class TestTranslatorIftmin(EhLogEdiTestCase):

    def test_iftmin_envelope_segments(self):
        outbound = self.partner_config.queue_outbound(
            self.iftmin, self._build_freight_job(),
        )
        outbound.action_queue()
        payload = outbound._payload_bytes().decode("utf-8")
        # Envelope segments are present.
        self.assertIn("UNB+", payload)
        self.assertIn("UNH+", payload)
        self.assertIn("BGM+340+", payload)  # Forwarding instruction
        self.assertIn("UNT+", payload)
        self.assertIn("UNZ+", payload)
        # Recipient identifier carries the partner_identifier.
        self.assertIn("EDI-PRT-001", payload)
        # Both NAD parties appear.
        self.assertIn("NAD+CZ+", payload)
        self.assertIn("NAD+CN+", payload)
        # Weight measurement is present.
        self.assertIn("MEA+AAE+G+KGM:1500.000", payload)
        # Volume measurement is present.
        self.assertIn("MEA+AAE+AAW+MTQ:8.500", payload)

    def test_iftmin_filename_template(self):
        outbound = self.partner_config.queue_outbound(
            self.iftmin, self._build_freight_job(),
        )
        outbound.action_queue()
        self.assertTrue(outbound.payload_filename.startswith("IFTMIN_"))
        self.assertTrue(outbound.payload_filename.endswith(".edi"))
