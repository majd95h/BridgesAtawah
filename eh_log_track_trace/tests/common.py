# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_track_trace tests."""
from datetime import date, datetime, timedelta

from odoo.tests import TransactionCase


class EhLogTrackTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({
            "name": "Track Test Customer",
            "email": "trackcustomer@example.com",
        })
        cls.driver = cls.env["eh.log.transport.driver"].create({
            "name": "Track Test Driver",
            "license_number": "TRK-001",
            "license_expiry_date": date.today() + timedelta(days=365),
            "company_id": cls.company.id,
        })
        cls.vehicle = cls.env["eh.log.transport.vehicle"].create({
            "registration": "TRK-VAN-001",
            "name": "Track Test Van",
            "vehicle_type": "van",
            "company_id": cls.company.id,
        })
        cls.code_in_transit = cls.env.ref(
            "eh_log_track_trace.event_code_in_transit"
        )
        cls.code_delivered = cls.env.ref(
            "eh_log_track_trace.event_code_delivered"
        )

    def _build_wave(self):
        return self.env["eh.log.last.mile.wave"].create({
            "scheduled_date": date.today(),
            "driver_id": self.driver.id,
            "vehicle_id": self.vehicle.id,
            "company_id": self.company.id,
        })

    def _build_delivery(self, wave=None, cod=0.0):
        base = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        return self.env["eh.log.last.mile.delivery"].create({
            "wave_id": wave.id if wave else False,
            "customer_id": self.customer.id,
            "scheduled_window_start": base,
            "scheduled_window_end": base + timedelta(hours=2),
            "package_count": 1,
            "cod_amount": cod,
            "company_id": self.company.id,
        })
