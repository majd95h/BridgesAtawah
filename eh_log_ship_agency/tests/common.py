# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_ship_agency tests."""
from datetime import datetime, timedelta

from odoo.tests import TransactionCase


# Real-world IMO checksum: 9074729 is the IMO for the container vessel
# Maersk Brani; the test uses it because the checksum is verifiable
# externally and the validator catches any change inside the suite.
TEST_IMO = "9074729"
TEST_IMO_ALT = "1234567"


class EhLogShipTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.port = cls.env["res.partner"].create({
            "name": "Port of Test",
            "is_company": True,
            "country_id": cls.env.ref("base.ae").id,
        })
        cls.principal = cls.env["res.partner"].create({
            "name": "Test Shipping Line",
            "is_company": True,
        })
        cls.berth = cls.env["eh.log.ship.berth"].create({
            "name": "Berth A1",
            "code": "A1",
            "port_partner_id": cls.port.id,
            "depth_m": 14.0,
            "max_loa_m": 350.0,
            "company_id": cls.company.id,
        })
        cls.vessel = cls.env["eh.log.ship.vessel"].create({
            "name": "Test Container Ship",
            "imo_number": TEST_IMO,
            "vessel_type": "container",
            "draft_m": 12.0,
            "length_overall_m": 300.0,
            "company_id": cls.company.id,
        })

    def _build_port_call(self, vessel=None, berth=None):
        return self.env["eh.log.ship.port.call"].create({
            "vessel_id": (vessel or self.vessel).id,
            "port_partner_id": self.port.id,
            "berth_id": (berth or self.berth).id,
            "principal_partner_id": self.principal.id,
            "eta_at": datetime.now() + timedelta(hours=4),
            "company_id": self.company.id,
        })
