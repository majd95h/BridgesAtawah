# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Carrier adapter base.

Lighter than the eh_log_base BaseAdapter: in-process dispatch without
the retry/breaker/audit-log apparatus. Carrier portal calls are
synchronous, idempotent at the application level, and don't need the
heavy-duty infrastructure used for customs adapters.

Concrete carrier adapters subclass this, set PROVIDER_CODE and
API_VERSION, and implement one method per message type. The
registration helper hooks the class into the central
eh_log_base.adapter_registry so the carrier profile can resolve it
by code.

The mock-mode shortcut: if the profile's is_mock flag is set, the
adapter's method is still called but the implementation returns
canned data without making any external call. This keeps the test
suite self-contained.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from odoo.addons.eh_log_base import adapter_registry
from odoo.addons.eh_log_base.exceptions import (
    AdapterValidationError,
    ConfigurationMissingError,
)

_logger = logging.getLogger(__name__)


# Message types every carrier adapter must implement. The portal will
# refuse to dispatch a message that is not in this set; extending the
# set requires explicit changes to this constant and to the adapter
# implementations, which is intentional.
MESSAGE_TYPES = (
    "rate_shop",
    "book",
    "cancel",
    "track_status",
    "schedules",
    "health_check",
)


@dataclass
class CarrierCallResult:
    ok: bool
    parsed: Optional[dict] = None
    error: str = ""
    raw_response: str = ""
    correlation_id: str = ""


class CarrierAdapter:
    """Base class for carrier portal adapters."""

    PROVIDER_CODE: str = ""
    API_VERSION: str = ""

    def __init__(self, env, profile):
        if not self.PROVIDER_CODE:
            raise ConfigurationMissingError(
                40,
                "Concrete carrier adapter is missing PROVIDER_CODE.",
            )
        if not self.API_VERSION:
            raise ConfigurationMissingError(
                41,
                "Concrete carrier adapter is missing API_VERSION.",
            )
        if profile.provider_code != self.PROVIDER_CODE:
            raise ConfigurationMissingError(
                42,
                f"Adapter {self.__class__.__name__} declares "
                f"PROVIDER_CODE {self.PROVIDER_CODE!r} but profile "
                f"{profile.display_name!r} carries "
                f"{profile.provider_code!r}.",
            )
        self.env = env
        self.profile = profile

    def call(
        self,
        message_type: str,
        payload: Any,
        related_model: Optional[str] = None,
    ) -> CarrierCallResult:
        if message_type not in MESSAGE_TYPES:
            raise AdapterValidationError(
                43,
                f"Unknown carrier message type {message_type!r}; "
                f"must be one of {MESSAGE_TYPES}.",
            )
        method = getattr(self, f"do_{message_type}", None)
        if method is None:
            raise AdapterValidationError(
                44,
                f"Carrier adapter {self.__class__.__name__} does not "
                f"implement message type {message_type!r}.",
            )
        try:
            return method(payload)
        except Exception as exc:
            _logger.exception(
                "Carrier %s call %s failed: %s",
                self.PROVIDER_CODE, message_type, exc,
            )
            return CarrierCallResult(
                ok=False,
                error=str(exc),
            )

    def health_check(self) -> CarrierCallResult:
        return self.call("health_check", {})


def register(provider_code, adapter_cls):
    """Register a carrier adapter with the central registry."""
    adapter_registry.register(provider_code, adapter_cls)
