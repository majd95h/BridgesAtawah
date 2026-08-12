# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Mock ocean carrier adapter.

Reference implementation for an ocean (FCL/LCL) carrier integration.
Returns deterministic canned data for every message type so the
rate-shop and booking flows are testable without external network
access.

Real ocean carrier adapters (Maersk EDI, Hapag-Lloyd EDI, Mediterranean
Shipping JSON) follow the same dispatch table and replace the stub
implementations with real serialise/parse calls. The CarrierAdapter
base does not constrain the wire format, only the message types.
"""
import logging
import uuid
from datetime import date, timedelta

from . import base

_logger = logging.getLogger(__name__)


# Per-mode pricing model used by the mock. Real adapters compute price
# from a rate sheet, surcharge tables, or live carrier API responses.
# Two service variants exposed so the rate-shop fan-out has more than
# one row to rank.
SERVICES = (
    ("OCEAN-STD", 1500.0, 28),
    ("OCEAN-EXP", 2200.0, 18),
)


class MockOceanAdapter(base.CarrierAdapter):
    PROVIDER_CODE = "mock_ocean"
    API_VERSION = "1.0"

    def do_rate_shop(self, payload):
        offers = []
        weight = (payload.get("cargo") or {}).get("weight_kg", 0.0)
        weight_factor = 1.0 + (weight / 20000.0)
        for service_name, base_price, transit_days in SERVICES:
            offers.append({
                "service_name": service_name,
                "transit_days": transit_days,
                "price": round(base_price * weight_factor, 2),
                "currency_code": "USD",
                "valid_until": (date.today() + timedelta(days=14)).isoformat(),
                "reference": f"MO-{uuid.uuid4().hex[:8].upper()}",
            })
        return base.CarrierCallResult(
            ok=True,
            parsed={"offers": offers},
            raw_response="",
        )

    def do_book(self, payload):
        return base.CarrierCallResult(
            ok=True,
            parsed={
                "booking_reference": (
                    f"MO-BKG-{uuid.uuid4().hex[:10].upper()}"
                ),
                "service_name": payload.get("service_name") or "OCEAN-STD",
            },
        )

    def do_cancel(self, payload):
        return base.CarrierCallResult(
            ok=True,
            parsed={
                "booking_reference": payload.get("booking_reference", ""),
                "status": "cancelled",
            },
        )

    def do_track_status(self, payload):
        return base.CarrierCallResult(
            ok=True,
            parsed={
                "booking_reference": payload.get("booking_reference", ""),
                "status_message": "in_transit",
            },
        )

    def do_schedules(self, payload):
        sailings = []
        for week in range(4):
            sailings.append({
                "voyage_reference": f"V{week:02d}",
                "etd": (date.today() + timedelta(days=7 * week)).isoformat(),
                "eta": (date.today() + timedelta(days=7 * week + 28)).isoformat(),
            })
        return base.CarrierCallResult(
            ok=True,
            parsed={"sailings": sailings},
        )

    def do_health_check(self, payload):
        return base.CarrierCallResult(ok=True, parsed={"status": "ok"})


base.register("mock_ocean", MockOceanAdapter)
