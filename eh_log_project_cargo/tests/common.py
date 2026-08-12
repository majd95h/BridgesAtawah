# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Shared fixtures for eh_log_project_cargo tests."""
from datetime import date, datetime, timedelta

from odoo.tests import TransactionCase


class EhLogProjectCargoTestCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env["res.partner"].create({
            "name": "Heavy Lift Customer",
            "is_company": True,
        })
        cls.origin = cls.env["res.partner"].create({
            "name": "Origin Yard",
            "is_company": True,
        })
        cls.destination = cls.env["res.partner"].create({
            "name": "Destination Site",
            "is_company": True,
        })
        cls.crane = cls.env["eh.log.project.cargo.equipment"].create({
            "name": "Crawler Crane LTM 1500",
            "code": "CRN-500",
            "equipment_type": "crane_crawler",
            "rated_capacity_t": 500.0,
            "max_boom_radius_m": 80.0,
            "company_id": cls.company.id,
        })
        cls.spmt = cls.env["eh.log.project.cargo.equipment"].create({
            "name": "Goldhofer SPMT",
            "code": "SPMT-12",
            "equipment_type": "spmt",
            "rated_capacity_t": 480.0,
            "spmt_axle_lines": 12,
            "spmt_modules_available": 4,
            "company_id": cls.company.id,
        })
        cls.escort = cls.env["eh.log.project.cargo.equipment"].create({
            "name": "Escort Pilot Vehicle",
            "code": "ESC-01",
            "equipment_type": "escort",
            "company_id": cls.company.id,
        })

    def _build_job(self):
        return self.env["eh.log.project.cargo.job"].create({
            "customer_partner_id": self.customer.id,
            "project_name": "Test Refinery Column",
            "origin_partner_id": self.origin.id,
            "destination_partner_id": self.destination.id,
            "target_start_date": date.today(),
            "target_end_date": date.today() + timedelta(days=14),
            "company_id": self.company.id,
        })

    def _add_oversized_item(self, job):
        return self.env["eh.log.project.cargo.item"].create({
            "job_id": job.id,
            "name": "Refinery Column",
            "quantity": 1,
            "length_m": 28.0,
            "width_m": 5.5,
            "height_m": 6.2,
            "weight_t": 240.0,
        })

    def _add_route_survey(self, job, chosen=False):
        return self.env["eh.log.project.cargo.route.survey"].create({
            "job_id": job.id,
            "name": "Coastal Highway Route",
            "distance_km": 110.0,
            "min_overhead_clearance_m": 7.0,
            "max_axle_load_t": 35.0,
            "is_chosen_route": chosen,
        })

    def _add_convoy(self, job, with_vehicles=True):
        convoy = self.env["eh.log.project.cargo.convoy"].create({
            "job_id": job.id,
            "scheduled_departure": datetime.now() + timedelta(days=1),
            "scheduled_arrival": datetime.now() + timedelta(days=1, hours=10),
        })
        if with_vehicles:
            self.env["eh.log.project.cargo.convoy.vehicle"].create({
                "convoy_id": convoy.id,
                "equipment_id": self.spmt.id,
                "role": "primary",
            })
            self.env["eh.log.project.cargo.convoy.vehicle"].create({
                "convoy_id": convoy.id,
                "equipment_id": self.escort.id,
                "role": "escort_lead",
            })
        return convoy

    def _add_permit(self, job, valid_days=30):
        return self.env["eh.log.project.cargo.permit"].create({
            "name": "Police Escort Permit",
            "job_id": job.id,
            "authority": "police",
            "valid_until": date.today() + timedelta(days=valid_days),
            "company_id": self.company.id,
        })
