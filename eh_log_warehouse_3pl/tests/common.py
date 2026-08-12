# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_warehouse_3pl tests."""
from datetime import date, timedelta

from odoo.tests import TransactionCase


class EhLogWarehouseTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({
            "name": "Acme 3PL Client",
            "is_company": True,
        })
        cls.facility = cls.env["eh.log.warehouse.facility"].create({
            "name": "Test Bonded Warehouse",
            "code": "TBW",
            "customs_status": "bonded",
            "company_id": cls.company.id,
        })
        cls.zone = cls.env["eh.log.warehouse.zone"].create({
            "name": "Bonded Bulk",
            "code": "BB",
            "facility_id": cls.facility.id,
            "purpose": "bonded",
        })
        cls.zone_outbound = cls.env["eh.log.warehouse.zone"].create({
            "name": "Outbound Staging",
            "code": "OB",
            "facility_id": cls.facility.id,
            "purpose": "staging",
        })
        cls.location = cls.env["eh.log.warehouse.location"].create({
            "name": "A1-01",
            "code": "A0101",
            "zone_id": cls.zone.id,
            "pallet_capacity": 4,
        })
        cls.location_alt = cls.env["eh.log.warehouse.location"].create({
            "name": "A1-02",
            "code": "A0102",
            "zone_id": cls.zone.id,
            "pallet_capacity": 4,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Test Pallet Product",
            "type": "consu",
        })
        cls.rate_card = cls.env["eh.log.warehouse.rate.card"].create({
            "name": "Standard Rate Card",
            "code": "STD",
            "company_id": cls.company.id,
        })
        for service, price in [
            ("storage_pallet_day", 1.5),
            ("handling_in", 5.0),
            ("handling_out", 6.0),
            ("monthly_minimum", 50.0),
        ]:
            cls.env["eh.log.warehouse.rate.line"].create({
                "rate_card_id": cls.rate_card.id,
                "service_type": service,
                "unit_price": price,
            })
        cls.client = cls.env["eh.log.warehouse.client"].create({
            "name": "Acme 3PL",
            "code": "ACME",
            "partner_id": cls.partner.id,
            "rate_card_id": cls.rate_card.id,
            "company_id": cls.company.id,
        })

    def _build_receipt(self, lines=None):
        Receipt = self.env["eh.log.warehouse.receipt"]
        receipt = Receipt.create({
            "client_id": self.client.id,
            "facility_id": self.facility.id,
            "expected_date": date.today(),
            "company_id": self.company.id,
        })
        for product, quantity, pallets, location in (lines or [
            (self.product, 100, 2, self.location),
        ]):
            self.env["eh.log.warehouse.receipt.line"].create({
                "receipt_id": receipt.id,
                "product_id": product.id,
                "quantity": quantity,
                "pallet_count": pallets,
                "destination_location_id": location.id if location else False,
            })
        return receipt

    def _build_pick(self, lines=None):
        Pick = self.env["eh.log.warehouse.pick"]
        pick = Pick.create({
            "client_id": self.client.id,
            "facility_id": self.facility.id,
            "planned_date": date.today(),
            "company_id": self.company.id,
        })
        for product, quantity, pallets, location in (lines or [
            (self.product, 50, 1, self.location),
        ]):
            self.env["eh.log.warehouse.pick.line"].create({
                "pick_id": pick.id,
                "product_id": product.id,
                "quantity": quantity,
                "pallet_count": pallets,
                "source_location_id": location.id if location else False,
            })
        return pick
