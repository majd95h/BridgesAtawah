# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""IFTSTA inbound: parse, apply, event emission on freight job."""
from .common import EhLogEdiTestCase


def _build_iftsta_payload(reference, status_code, occurred_yyyymmdd, location, description=""):
    """Construct a minimal IFTSTA EDIFACT payload for the parser."""
    parts = [
        "UNB+UNOC:3+SENDER:ZZZ+RECEIVER:ZZZ+260101:1200+1",
        "UNH+1+IFTSTA:D:96B:UN",
        "BGM+77+REF1+9",
        f"DTM+137:{occurred_yyyymmdd}:102",
        f"RFF+CO:{reference}",
        f"STS+{status_code}:::EH",
        f"DTM+334:{occurred_yyyymmdd}:102",
        f"LOC+9+{location}::95",
    ]
    if description:
        parts.append(f"FTX+AAI+++{description}:::EN")
    parts.append("UNT+8+1")
    parts.append("UNZ+1+1")
    return "'".join(parts).encode("utf-8") + b"'"


class TestInboundIftsta(EhLogEdiTestCase):

    def test_inbound_lifecycle_emits_track_event(self):
        job = self._build_freight_job()
        payload = _build_iftsta_payload(
            reference=job.name,
            status_code="1",
            occurred_yyyymmdd="20260105",
            location="AEJEA",
            description="Vessel sailed",
        )
        Inbound = self.env["eh.log.edi.inbound"]
        inbound = Inbound.receive(
            partner_config=self.partner_config,
            message_type=self.iftsta,
            payload_bytes=payload,
            filename="iftsta_test.edi",
        )
        self.assertEqual(inbound.state, "received")
        inbound.action_parse()
        self.assertEqual(inbound.state, "parsed")
        self.assertIn(job.name, inbound.parsed_payload)
        inbound.action_process()
        self.assertEqual(inbound.state, "processed")
        events = self.env["eh.log.track.event"].search([
            ("res_model", "=", "eh.log.freight.job"),
            ("res_id", "=", job.id),
            ("code", "=", "in_transit"),
        ])
        self.assertTrue(events)

    def test_inbound_unknown_reference_apply_yields_no_target(self):
        payload = _build_iftsta_payload(
            reference="DOES-NOT-EXIST",
            status_code="2",
            occurred_yyyymmdd="20260105",
            location="AEJEA",
        )
        Inbound = self.env["eh.log.edi.inbound"]
        inbound = Inbound.receive(
            partner_config=self.partner_config,
            message_type=self.iftsta,
            payload_bytes=payload,
        )
        inbound.action_parse()
        inbound.action_process()
        # No matching freight job means apply returns an empty
        # recordset; processing still completes (the inbound is
        # not 'rejected'), the payload is just ignored.
        self.assertEqual(inbound.state, "processed")
        self.assertFalse(inbound.target_record_ref)
