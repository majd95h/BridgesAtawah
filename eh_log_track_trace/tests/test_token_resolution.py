# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Token resolution: tokens are stable, opaque, and round-trip cleanly."""
from .common import EhLogTrackTestCase


class TestTokenResolution(EhLogTrackTestCase):

    def test_token_is_stable_for_same_record(self):
        delivery = self._build_delivery()
        first = delivery.tracking_token
        delivery.invalidate_recordset()
        second = delivery.tracking_token
        self.assertEqual(first, second)

    def test_token_resolves_back_to_record(self):
        delivery = self._build_delivery()
        token = delivery.tracking_token
        Trackable = self.env["eh.log.track.trackable"]
        resolved = Trackable.resolve_token(token)
        self.assertEqual(resolved._name, delivery._name)
        self.assertEqual(resolved.id, delivery.id)

    def test_token_differs_between_records(self):
        d1 = self._build_delivery()
        d2 = self._build_delivery()
        self.assertNotEqual(d1.tracking_token, d2.tracking_token)

    def test_unknown_token_returns_falsy(self):
        Trackable = self.env["eh.log.track.trackable"]
        self.assertFalse(Trackable.resolve_token("0" * 32))
        self.assertFalse(Trackable.resolve_token(""))
        self.assertFalse(Trackable.resolve_token("too_short"))

    def test_track_url_uses_configured_base(self):
        Param = self.env["ir.config_parameter"].sudo()
        Param.set_param(
            "eh_log_track_trace.public_base_url",
            "https://track.example.com",
        )
        delivery = self._build_delivery()
        delivery.invalidate_recordset()
        self.assertTrue(delivery.track_url.startswith(
            "https://track.example.com/track/"
        ))
