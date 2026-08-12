# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_edi tests."""
from odoo.tests import TransactionCase


class EhLogEdiTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.shipper = cls.env["res.partner"].create({
            "name": "Test Shipper Ltd",
            "ref": "SHP-001",
            "is_company": True,
            "country_id": cls.env.ref("base.in").id,
        })
        cls.consignee = cls.env["res.partner"].create({
            "name": "Test Consignee LLC",
            "ref": "CON-001",
            "is_company": True,
            "country_id": cls.env.ref("base.ae").id,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Test EDI Partner",
            "ref": "EDI-PRT-001",
            "is_company": True,
        })
        cls.transport = cls.env["eh.log.edi.transport"].create({
            "name": "Mock Transport",
            "code": "MOCK",
            "protocol": "mock",
            "company_id": cls.company.id,
        })
        cls.iftmin = cls.env.ref("eh_log_edi.message_type_iftmin")
        cls.iftsta = cls.env.ref("eh_log_edi.message_type_iftsta")
        cls.partner_config = cls.env["eh.log.edi.partner"].create({
            "name": "Test EDI Partner Config",
            "partner_id": cls.partner.id,
            "partner_identifier": "EDI-PRT-001",
            "transport_id": cls.transport.id,
            "message_type_ids": [(6, 0, [cls.iftmin.id, cls.iftsta.id])],
            "is_default": True,
            "company_id": cls.company.id,
        })

    def _build_freight_job(self):
        # Freight jobs require a confirmed sale order in the standard
        # creation path; the test bypasses that with a direct create
        # which works because the model permits it.
        Job = self.env["eh.log.freight.job"]
        return Job.create({
            "customer_id": self.shipper.id,
            "shipper_id": self.shipper.id,
            "consignee_id": self.consignee.id,
            "gross_weight_kg": 1500.0,
            "volume_cbm": 8.5,
            "company_id": self.company.id,
        })
