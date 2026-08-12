# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""COD: required at delivery, cap at expected, wave aggregation."""
from odoo.exceptions import UserError

from .common import EhLogLastMileTestCase


class TestCodCapture(EhLogLastMileTestCase):

    def test_cod_required_at_delivery_when_set(self):
        delivery = self._add_delivery(cod=200.0)
        delivery.action_set_out_for_delivery()
        with self.assertRaises(UserError) as ctx:
            delivery.action_mark_delivered(recipient_name="X")
        self.assertIn("[EHL-LM-DEL-002]", str(ctx.exception))

    def test_cod_cannot_exceed_expected(self):
        delivery = self._add_delivery(cod=200.0)
        delivery.action_set_out_for_delivery()
        with self.assertRaises(UserError) as ctx:
            delivery.action_mark_delivered(
                recipient_name="X",
                cod_collected=300.0,
                cod_method="cash",
            )
        self.assertIn("[EHL-LM-DEL-003]", str(ctx.exception))

    def test_cod_collection_captured(self):
        delivery = self._add_delivery(cod=200.0)
        delivery.action_set_out_for_delivery()
        delivery.action_mark_delivered(
            recipient_name="X",
            cod_collected=200.0,
            cod_method="card",
        )
        self.assertEqual(delivery.cod_collected_amount, 200.0)
        self.assertEqual(delivery.cod_collection_method, "card")

    def test_wave_aggregates_cod(self):
        wave = self._build_wave()
        d1 = self._add_delivery(wave=wave, cod=100.0)
        d2 = self._add_delivery(wave=wave, cod=250.0, customer=self.customer_b)
        wave.action_dispatch()
        wave.action_set_in_progress()
        d1.action_mark_delivered(
            recipient_name="X", cod_collected=100.0, cod_method="cash",
        )
        d2.action_mark_delivered(
            recipient_name="Y", cod_collected=200.0, cod_method="card",
        )
        wave.invalidate_recordset()
        self.assertEqual(wave.cod_expected, 350.0)
        self.assertEqual(wave.cod_collected, 300.0)
        self.assertEqual(wave.cod_outstanding, 50.0)

    def test_completion_pct_aggregate(self):
        wave = self._build_wave()
        d1 = self._add_delivery(wave=wave)
        d2 = self._add_delivery(wave=wave, customer=self.customer_b)
        wave.action_dispatch()
        d1.action_mark_delivered(recipient_name="X")
        wave.invalidate_recordset()
        self.assertEqual(wave.completion_pct, 50.0)
