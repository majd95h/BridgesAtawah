# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_transport tests."""
from datetime import date, timedelta

from odoo.tests import TransactionCase


class EhLogTransportTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({
            "name": "Test Transport Customer",
            "is_company": True,
        })
        cls.pickup_partner = cls.env["res.partner"].create({"name": "Pickup Warehouse"})
        cls.delivery_partner = cls.env["res.partner"].create({"name": "Delivery Site"})

        cls.vehicle = cls.env["eh.log.transport.vehicle"].create({
            "registration": "TEST-001",
            "name": "Test Truck",
            "vehicle_type": "rigid",
            "company_id": cls.company.id,
        })
        cls.trailer = cls.env["eh.log.transport.vehicle"].create({
            "registration": "TR-001",
            "name": "Test Trailer",
            "vehicle_type": "trailer",
            "company_id": cls.company.id,
        })
        cls.driver = cls.env["eh.log.transport.driver"].create({
            "name": "Test Driver",
            "license_number": "L-001",
            "license_expiry_date": date.today() + timedelta(days=365),
            "company_id": cls.company.id,
        })

    def _build_trip(self, **overrides):
        from datetime import datetime
        vals = {
            "customer_id": self.customer.id,
            "company_id": self.company.id,
            "pickup_partner_id": self.pickup_partner.id,
            "delivery_partner_id": self.delivery_partner.id,
            "pickup_planned_at": datetime(2026, 6, 1, 8, 0),
            "delivery_planned_at": datetime(2026, 6, 1, 18, 0),
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
        }
        vals.update(overrides)
        return self.env["eh.log.transport.trip"].create(vals)
