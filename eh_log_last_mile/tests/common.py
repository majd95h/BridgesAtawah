# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_last_mile tests."""
from datetime import date, datetime, timedelta

from odoo.tests import TransactionCase


class EhLogLastMileTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer_a = cls.env["res.partner"].create({"name": "Test Customer A"})
        cls.customer_b = cls.env["res.partner"].create({"name": "Test Customer B"})
        cls.driver = cls.env["eh.log.transport.driver"].create({
            "name": "Last Mile Driver",
            "license_number": "LM-001",
            "license_expiry_date": date.today() + timedelta(days=365),
            "company_id": cls.company.id,
        })
        cls.vehicle = cls.env["eh.log.transport.vehicle"].create({
            "registration": "VAN-001",
            "name": "Delivery Van",
            "vehicle_type": "van",
            "company_id": cls.company.id,
        })

    def _build_wave(self, **overrides):
        from datetime import date
        vals = {
            "scheduled_date": date.today(),
            "driver_id": self.driver.id,
            "vehicle_id": self.vehicle.id,
            "company_id": self.company.id,
        }
        vals.update(overrides)
        return self.env["eh.log.last.mile.wave"].create(vals)

    def _add_delivery(self, wave=None, customer=None, cod=0.0, packages=1, **overrides):
        from datetime import datetime, timedelta
        base = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        vals = {
            "wave_id": wave.id if wave else False,
            "customer_id": (customer or self.customer_a).id,
            "scheduled_window_start": base,
            "scheduled_window_end": base + timedelta(hours=2),
            "package_count": packages,
            "cod_amount": cod,
            "company_id": self.company.id,
        }
        vals.update(overrides)
        return self.env["eh.log.last.mile.delivery"].create(vals)
