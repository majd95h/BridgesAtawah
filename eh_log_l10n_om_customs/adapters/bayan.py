# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Bayan (Oman) customs adapter.

Royal Oman Police Customs single window. JSON contract.
"""
import json
import logging

from odoo.addons.eh_log_base import adapter_registry
from odoo.addons.eh_log_base.adapters.base import BaseAdapter
from odoo.addons.eh_log_base.exceptions import AdapterValidationError

_logger = logging.getLogger(__name__)


class BayanAdapter(BaseAdapter):
    """Concrete Bayan adapter."""

    PROVIDER_CODE = "bayan"
    API_VERSION = "1.0"
    MOCK_FIXTURE_DIR = "bayan"

    def serialize(self, message_type: str, payload) -> bytes:
        if message_type == "declaration_submit":
            return self._serialize_declaration_submit(payload)
        if message_type == "declaration_status":
            return self._serialize_declaration_status(payload)
        if message_type == "health_check":
            return b""
        raise AdapterValidationError(
            80,
            f"Bayan adapter does not implement message type {message_type!r}.",
        )

    def parse(self, message_type: str, raw: str):
        if not raw:
            return {}
        if message_type == "declaration_submit":
            return self._parse_declaration_submit(raw)
        if message_type == "declaration_status":
            return self._parse_declaration_status(raw)
        if message_type == "health_check":
            return self._parse_health_check(raw)
        raise AdapterValidationError(
            81,
            f"Bayan adapter cannot parse a response for message type "
            f"{message_type!r}.",
        )

    def _endpoint_for(self, message_type: str) -> str:
        base = self.profile.endpoint_url or ""
        if not base:
            return base
        suffix_map = {
            "declaration_submit": "/api/v1/declarations",  # noqa: gcclog-hardcode Bayan endpoint path per documented contract
            "declaration_status": "/api/v1/declarations/status",  # noqa: gcclog-hardcode Bayan endpoint path per documented contract
            "health_check": "/api/v1/health",  # noqa: gcclog-hardcode Bayan endpoint path per documented contract
        }
        return f"{base.rstrip('/')}{suffix_map.get(message_type, '')}"

    def _http_method(self, message_type: str) -> str:
        if message_type in ("declaration_status", "health_check"):
            return "GET"
        return "POST"

    def _headers_for(self, message_type: str) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"erpheritage-logistics-bayan/{self.API_VERSION}",
        }
        try:
            api_key = self.env["eh.log.credentials"].get(
                "bayan_api_key",
                env_vars=["EH_LOG_BAYAN_API_KEY", "BAYAN_API_KEY"],
                param_key="bayan.api_key",
                company_id=self.profile.company_id.id,
            )
            headers["Authorization"] = f"Bearer {api_key}"
        except Exception:
            pass
        return headers

    def _serialize_declaration_submit(self, payload: dict) -> bytes:
        envelope = {
            "declarationType": payload.get("declaration_type") or "",
            "brokerReference": payload.get("broker_reference") or "",
            "declarationDate": payload.get("declaration_date") or "",
            "currency": payload.get("currency") or "",
            "parties": {
                "importer": (payload.get("importer") or {}),
                "exporter": (payload.get("exporter") or {}),
            },
            "totals": {
                "customsValue": payload.get("customs_value") or 0,
                "dutyAmount": payload.get("duty_amount") or 0,
                "vatAmount": payload.get("vat_amount") or 0,
                "payableAmount": payload.get("payable_amount") or 0,
            },
            "lines": [
                {
                    "lineNumber": index,
                    "hsCode": line.get("hs_code") or "",
                    "description": line.get("description") or "",
                    "countryOfOrigin": line.get("country_of_origin") or "",
                    "quantity": line.get("quantity") or 0,
                    "unitValue": line.get("unit_value") or 0,
                    "customsValue": line.get("customs_value") or 0,
                    "dutyRatePct": line.get("duty_rate_pct") or 0,
                    "vatRatePct": line.get("vat_rate_pct") or 0,
                    "dutyAmount": line.get("duty_amount") or 0,
                    "vatAmount": line.get("vat_amount") or 0,
                }
                for index, line in enumerate(payload.get("lines") or [], start=1)
            ],
        }
        return json.dumps(envelope, ensure_ascii=False).encode("utf-8")

    def _serialize_declaration_status(self, payload: dict) -> bytes:
        return json.dumps({
            "regulatorReference": payload.get("regulator_reference") or "",
        }).encode("utf-8")

    def _parse_declaration_submit(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdapterValidationError(
                82,
                f"Bayan returned a malformed JSON response. Parse error: {exc}.",
            ) from exc
        return {
            "regulator_reference": data.get("regulatorReference"),
            "status": data.get("status"),
            "message": data.get("message"),
            "errors": [
                {
                    "code": err.get("code"),
                    "message": err.get("message"),
                    "field": err.get("field"),
                }
                for err in (data.get("errors") or [])
            ],
        }

    def _parse_declaration_status(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "unknown", "raw": raw}
        return {
            "regulator_reference": data.get("regulatorReference"),
            "status": data.get("status"),
            "assessment_amount": data.get("assessmentAmount"),
        }

    def _parse_health_check(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
            return {"status": data.get("status") or "OK"}
        except json.JSONDecodeError:
            return {"status": "OK" if raw.strip() else "EMPTY"}


adapter_registry.register("bayan", BayanAdapter)
