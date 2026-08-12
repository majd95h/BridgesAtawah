# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""IFTSTA inbound translator.

UN/EDIFACT D.96B IFTSTA ('International Multimodal Status Report').
Received from a carrier or upstream agent reporting on the progress
of a shipment. The translator parses the EDIFACT segments, finds the
matching freight job by reference, and emits a normalised tracking
event through the trackable mixin.

Status codes are mapped through a small lookup. Unknown codes are
recorded as the generic 'in_transit' event with the original code
preserved on the description.
"""
from datetime import datetime

from . import base


# IFTSTA status code -> normalized tracking event code. The list
# covers the high-frequency carrier statuses; unmapped codes fall
# through to the 'in_transit' default.
STATUS_CODE_MAP = {
    "1":  "in_transit",       # In transit
    "2":  "delivered",        # Delivery completed
    "5":  "picked_up",        # Goods received from shipper
    "6":  "at_pickup",        # At pickup location
    "7":  "at_delivery",      # At delivery location
    "8":  "customs_hold",     # Customs status reported
    "9":  "customs_cleared",  # Customs clearance complete
    "12": "delivery_failed",  # Goods not delivered
    "27": "exception",        # Exception
    "55": "out_for_delivery", # Out for delivery
    "65": "arrived",          # Arrival
}


class IftstaInboundTranslator(base.InboundTranslator):
    MESSAGE_CODE = "IFTSTA"
    ENCODING = "edifact"

    def parse(self, payload, partner) -> dict:
        segments = self.split_segments(payload)
        result = {
            "shipment_reference": "",
            "status_code": "",
            "occurred_at": "",
            "location": "",
            "description": "",
        }
        for segment in segments:
            elements = self.split_elements(segment)
            tag = elements[0] if elements else ""
            if tag == "RFF" and len(elements) >= 2:
                # Reference identification. CO = Customer reference,
                # AAM = master reference number. Either is acceptable
                # for matching back to the freight job.
                composite = elements[1].split(":")
                if len(composite) >= 2 and composite[0] in ("CO", "AAM", "CN"):
                    result["shipment_reference"] = composite[1]
            elif tag == "STS" and len(elements) >= 2:
                composite = elements[1].split(":")
                if len(composite) >= 1:
                    result["status_code"] = composite[0]
            elif tag == "DTM" and len(elements) >= 2:
                composite = elements[1].split(":")
                if len(composite) >= 3 and composite[0] in ("334", "335"):  # noqa: gcclog-hardcode UN/EDIFACT D.96B DTM qualifier codes for status reporting
                    result["occurred_at"] = composite[1]
            elif tag == "LOC" and len(elements) >= 3:
                composite = elements[2].split(":")
                if composite:
                    result["location"] = composite[0]
            elif tag == "FTX" and len(elements) >= 5:
                # Free text. Element 4 is the actual text composite.
                composite = elements[4].split(":")
                result["description"] = composite[0]
        return result

    def apply(self, parsed, partner):
        if not parsed.get("shipment_reference"):
            return self.env["eh.log.track.event"]
        Job = self.env["eh.log.freight.job"].sudo()
        job = Job.search([
            "|",
            ("name", "=", parsed["shipment_reference"]),
            ("tracking_reference", "=", parsed["shipment_reference"]),
        ], limit=1)
        if not job:
            return self.env["eh.log.track.event"]
        normalised_code = STATUS_CODE_MAP.get(
            parsed.get("status_code", ""), "in_transit",
        )
        description = parsed.get("description") or ""
        if parsed.get("status_code") and not description:
            description = f"IFTSTA status {parsed['status_code']}"
        occurred = self._parse_dtm(parsed.get("occurred_at", ""))
        return job.log_track_event(
            normalised_code,
            description=description,
            location=parsed.get("location") or "",
            occurred_at=occurred,
            source="api",
        )

    def _parse_dtm(self, value):
        if not value:
            return False
        # CCYYMMDDHHMM (102 / 203 format) - try the longer first.
        for fmt in ("%Y%m%d%H%M", "%Y%m%d", "%y%m%d%H%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return False


base.register("IFTSTA", "in", IftstaInboundTranslator)
