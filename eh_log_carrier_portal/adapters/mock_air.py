# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Mock air carrier adapter.

Reference implementation for an air freight integration. Pricing
behaviour mirrors a chargeable-weight model: the higher of actual
weight and volumetric weight drives the rate. Real air adapters
(IATA Cargo-XML, Lufthansa eCargo) keep the same dispatch table and
swap in the wire-level integration.
"""
import logging
import uuid
from datetime import date, timedelta

from . import base

_logger = logging.getLogger(__name__)


# Volumetric divisor for IATA chargeable weight (kg per cubic metre).
# 167 is the standard divisor; carriers occasionally negotiate
# different values, but the mock uses the IATA default.
VOLUMETRIC_DIVISOR = 167.0  # noqa: gcclog-hardcode IATA Resolution 502 standard


# Service variants exposed by the mock air adapter.
SERVICES = (
    ("AIR-STD", 4.5, 5),
    ("AIR-EXP", 7.2, 2),
)


class MockAirAdapter(base.CarrierAdapter):
    PROVIDER_CODE = "mock_air"
    API_VERSION = "1.0"

    def do_rate_shop(self, payload):
        cargo = payload.get("cargo") or {}
        actual_weight = cargo.get("weight_kg", 0.0)
        volume_cbm = cargo.get("volume_cbm", 0.0)
        volumetric_weight = volume_cbm * VOLUMETRIC_DIVISOR
        chargeable = max(actual_weight, volumetric_weight, 1.0)
        offers = []
        for service_name, rate_per_kg, transit_days in SERVICES:
            offers.append({
                "service_name": service_name,
                "transit_days": transit_days,
                "price": round(chargeable * rate_per_kg, 2),
                "currency_code": "USD",
                "valid_until": (date.today() + timedelta(days=7)).isoformat(),
                "reference": f"MA-{uuid.uuid4().hex[:8].upper()}",
            })
        return base.CarrierCallResult(
            ok=True,
            parsed={"offers": offers},
        )

    def do_book(self, payload):
        return base.CarrierCallResult(
            ok=True,
            parsed={
                "booking_reference": (
                    f"MA-AWB-{uuid.uuid4().hex[:10].upper()}"
                ),
                "service_name": payload.get("service_name") or "AIR-STD",
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
                "status_message": "departed",
            },
        )

    def do_schedules(self, payload):
        flights = []
        for day_offset in range(7):
            flights.append({
                "flight_reference": f"F{day_offset:02d}",
                "etd": (date.today() + timedelta(days=day_offset)).isoformat(),
                "eta": (
                    date.today() + timedelta(days=day_offset, hours=8)
                ).isoformat(),
            })
        return base.CarrierCallResult(
            ok=True,
            parsed={"flights": flights},
        )

    def do_health_check(self, payload):
        return base.CarrierCallResult(ok=True, parsed={"status": "ok"})


base.register("mock_air", MockAirAdapter)
