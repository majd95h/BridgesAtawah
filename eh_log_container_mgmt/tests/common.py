# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_container_mgmt tests."""
from datetime import datetime, timedelta, date

from odoo.tests import TransactionCase


class EhLogContainerMgmtTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Operator + sale order + freight job + container fixture chain.
        cls.customer = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.depot_origin = cls.env["eh.log.container.mgmt.depot"].create({
            "code": "TEST-ORIGIN",
            "name": "Test Origin Depot",
            "depot_kind": "port_terminal",
            "company_id": cls.company.id,
        })
        cls.depot_destination = cls.env["eh.log.container.mgmt.depot"].create({
            "code": "TEST-DEST",
            "name": "Test Destination Depot",
            "depot_kind": "inland_depot",
            "company_id": cls.company.id,
        })

        cls.iso_40hc = cls.env.ref("eh_log_freight.iso_45g1")

        # Build a freight job through the sale order spawn path
        cls.order = cls.env["sale.order"].create({
            "partner_id": cls.customer.id,
            "company_id": cls.company.id,
            "eh_log_is_logistics": True,
            "eh_log_mode": "sea",
            "eh_log_direction": "import",
        })
        cls.env["sale.order.line"].create({
            "order_id": cls.order.id,
            "name": "FCL freight",
            "product_uom_qty": 1.0,
            "price_unit": 1500.0,
        })
        cls.order.action_confirm()
        cls.order.invalidate_recordset()
        cls.job = cls.order.eh_log_freight_job_ids[:1]

        cls.container = cls.env["eh.log.freight.container"].create({
            "job_id": cls.job.id,
            "iso_type_id": cls.iso_40hc.id,
            "container_number": "MSCU1234566",
        })

    def _make_movement(self, kind, depot=None, when=None, **overrides):
        vals = {
            "container_id": self.container.id,
            "movement_kind": kind,
            "depot_id": (depot or self.depot_origin).id,
            "happened_at": when or datetime.now(),
        }
        vals.update(overrides)
        return self.env["eh.log.container.mgmt.movement"].create(vals)
