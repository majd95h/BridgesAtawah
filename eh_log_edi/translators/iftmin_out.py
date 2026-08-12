# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""IFTMIN outbound translator.

UN/EDIFACT D.96B IFTMIN ('Forwarding Instruction'). Sent from a
forwarder to an actual carrier or upstream agent to instruct them
to handle a shipment. Driven by the freight job.

Implementation note: this is a working subset of the full IFTMIN
spec. Production deployments often need additional dangerous-goods,
temperature, and customs-status segments depending on the partner's
schema variant; those can be appended in a per-partner translator
override that subclasses this one.
"""
from datetime import datetime

from . import base


class IftminOutboundTranslator(base.OutboundTranslator):
    MESSAGE_CODE = "IFTMIN"
    SOURCE_MODEL = "eh.log.freight.job"
    ENCODING = "edifact"

    def build(self, record, partner) -> bytes:
        record.ensure_one()
        now = datetime.utcnow()
        timestamp = now.strftime("%y%m%d:%H%M")

        # UNB/UNH envelope are minimal; partner identifiers come from
        # the partner config. Real implementations swap in the
        # partner's preferred qualifier, control numbers from a
        # dedicated counter, etc.
        sender_id = partner._self_party_identifier()
        recipient_id = partner.partner_identifier or partner.partner_id.ref or ""
        control_ref = (
            self.env["ir.sequence"].next_by_code("eh.log.edi.unb.control")
            or "1"
        )
        message_ref = (
            self.env["ir.sequence"].next_by_code("eh.log.edi.unh.message")
            or "1"
        )

        segments = [
            self.edifact_segment(
                "UNB",
                "UNOC:3",
                f"{sender_id}:ZZZ",
                f"{recipient_id}:ZZZ",
                timestamp,
                control_ref,
            ),
            self.edifact_segment(
                "UNH",
                message_ref,
                "IFTMIN:D:96B:UN",
            ),
            # BGM: Beginning of Message. 340 = Forwarding instruction.
            self.edifact_segment("BGM", "340", record.name, "9"),
            # DTM: shipment date - 137 means "document/message date".
            self.edifact_segment("DTM", f"137:{now.strftime('%Y%m%d')}:102"),
        ]

        # NAD: party identification segments.
        if record.shipper_id:
            segments.append(self._nad("CZ", record.shipper_id))
        if record.consignee_id:
            segments.append(self._nad("CN", record.consignee_id))

        # GID: goods-item details. One segment per cargo type;
        # collapse to a single item on the freight-job level since
        # IFTMIN only requires per-item visibility for breaking
        # down a multi-package booking.
        segments.append(self.edifact_segment("GID", "1", "1:CT"))

        # MEA: weight measurement (KGM = kilograms).
        if record.gross_weight_kg:
            segments.append(
                self.edifact_segment(
                    "MEA",
                    "AAE",
                    "G",
                    f"KGM:{record.gross_weight_kg:.3f}",
                ),
            )

        # MEA: volume measurement (MTQ = cubic metres).
        if record.volume_cbm:
            segments.append(
                self.edifact_segment(
                    "MEA",
                    "AAE",
                    "AAW",
                    f"MTQ:{record.volume_cbm:.3f}",
                ),
            )

        segments.append(self.edifact_segment("UNT", str(len(segments) - 1), message_ref))
        segments.append(self.edifact_segment("UNZ", "1", control_ref))

        return ("".join(segments)).encode("utf-8")

    def _nad(self, qualifier: str, partner_record) -> str:
        """Compose a NAD party-identification segment."""
        # Strip the EDIFACT reserved characters from free-text fields
        # before they go on the wire. Apostrophe ends a segment, plus
        # separates elements, colon separates components.
        def clean(value: str) -> str:
            for char in ("'", "+", ":", "?"):
                value = (value or "").replace(char, " ")
            return value.strip()

        identifier = (
            (partner_record.ref or partner_record.vat or partner_record.id)
        )
        return self.edifact_segment(
            "NAD",
            qualifier,
            f"{identifier}::91",
            "",
            clean(partner_record.name),
            clean(partner_record.street or ""),
            clean(partner_record.city or ""),
            clean(partner_record.zip or ""),
            "",
            (partner_record.country_id.code or "")[:2],
        )


base.register("IFTMIN", "out", IftminOutboundTranslator)
