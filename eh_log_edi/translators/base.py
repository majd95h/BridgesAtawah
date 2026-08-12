# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Translator base + registry.

A translator turns an Odoo record into the bytes that go on the
wire (outbound) or turns received bytes into a normalised dict the
inbound handler can act on (inbound). Each translator declares:

* ``MESSAGE_CODE`` - the EDIFACT or X12 message identifier
* ``DIRECTION`` - 'out' or 'in'
* ``SOURCE_MODEL`` - for outbound, the Odoo model translatable
* ``ENCODING`` - 'edifact' or 'x12'

Outbound translators implement ``build(record, partner)`` returning
bytes. Inbound translators implement ``parse(payload, partner)``
returning a dict and ``apply(parsed, partner, env)`` returning the
list of records affected.

A central registry maps the (message_code, direction) tuple to the
translator class. The eh.log.edi.message.type record carries the
message_code; the outbound dispatcher resolves the translator at
dispatch time.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

_logger = logging.getLogger(__name__)

# Registry keyed by (message_code, direction). Direct mutation is
# fine because every translator module registers itself at import
# time, and the import order is locked by the package __init__.
_REGISTRY: Dict[tuple, Type] = {}


def register(message_code: str, direction: str, translator_cls: Type) -> None:
    if direction not in ("out", "in"):
        raise ValueError(
            f"Direction must be 'out' or 'in'; got {direction!r}."
        )
    key = (message_code, direction)
    _REGISTRY[key] = translator_cls


def get(message_code: str, direction: str) -> Optional[Type]:
    return _REGISTRY.get((message_code, direction))


def all_codes() -> list:
    return sorted({code for code, _ in _REGISTRY.keys()})


# ---------------------------------------------------------------------
# Base classes (concrete translators inherit one of these)
# ---------------------------------------------------------------------

class OutboundTranslator:
    """Builds the wire payload for an outbound message."""

    MESSAGE_CODE: str = ""
    SOURCE_MODEL: str = ""
    ENCODING: str = "edifact"

    def __init__(self, env):
        self.env = env

    def build(self, record, partner) -> bytes:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build()."
        )

    # ------------------------------------------------------------------
    # EDIFACT segment helpers (shared)
    # ------------------------------------------------------------------
    @staticmethod
    def edifact_segment(tag: str, *elements: Any) -> str:
        """Compose one EDIFACT segment.

        Element separator is '+'; terminator is "'". Composite
        elements are joined with ':' by the caller before being
        passed in. No escaping is done here; callers are responsible
        for stripping reserved characters from free-text values.
        """
        joined = "+".join([tag] + [str(e) for e in elements])
        return joined + "'"


class InboundTranslator:
    """Parses an inbound payload into a normalised dict and applies it."""

    MESSAGE_CODE: str = ""
    ENCODING: str = "edifact"

    def __init__(self, env):
        self.env = env

    def parse(self, payload: bytes, partner) -> dict:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement parse()."
        )

    def apply(self, parsed: dict, partner) -> Any:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement apply()."
        )

    # ------------------------------------------------------------------
    # EDIFACT segment helpers (shared)
    # ------------------------------------------------------------------
    @staticmethod
    def split_segments(payload: bytes) -> list[str]:
        """Split a raw EDIFACT payload into segments.

        Tolerates trailing whitespace and CRLF after each segment
        terminator, which real EDI files commonly carry.
        """
        text = payload.decode("utf-8", errors="replace")
        segments = []
        for raw in text.split("'"):
            cleaned = raw.replace("\r", "").replace("\n", "").strip()
            if cleaned:
                segments.append(cleaned)
        return segments

    @staticmethod
    def split_elements(segment: str) -> list[str]:
        return segment.split("+")
