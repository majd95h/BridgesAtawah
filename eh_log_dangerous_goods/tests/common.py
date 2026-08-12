# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_dangerous_goods tests."""
from odoo.tests import TransactionCase


class EhLogDgTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.shipper = cls.env["res.partner"].create({"name": "Test DG Shipper"})
        cls.consignee = cls.env["res.partner"].create({"name": "Test DG Consignee"})
        cls.un_acetone = cls.env.ref("eh_log_dangerous_goods.un_1090")
        cls.un_lpg = cls.env.ref("eh_log_dangerous_goods.un_1965")
        cls.un_lithium = cls.env.ref("eh_log_dangerous_goods.un_3480")
        cls.un_h2so4 = cls.env.ref("eh_log_dangerous_goods.un_1830")

    def _build_declaration(self, mode="sea"):
        return self.env["eh.log.dg.declaration"].create({
            "mode": mode,
            "company_id": self.company.id,
            "shipper_id": self.shipper.id,
            "consignee_id": self.consignee.id,
            "emergency_contact_name": "Ops Centre",
            "emergency_contact_phone": "+971 4 555 0100",
        })

    def _add_line(self, declaration, un_number, qty=10.0, packages=2, pkg="20 fibreboard boxes"):
        return self.env["eh.log.dg.declaration.line"].create({
            "declaration_id": declaration.id,
            "un_number_id": un_number.id,
            "package_count": packages,
            "net_quantity": qty,
            "net_quantity_uom": "kg",
            "packaging_description": pkg,
        })
