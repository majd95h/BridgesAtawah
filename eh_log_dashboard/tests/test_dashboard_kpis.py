# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dashboard: KPI computes, soft-module flags, drill-down actions."""
from odoo.tests import TransactionCase


class TestDashboardKpis(TransactionCase):

    def test_dashboard_create_yields_record(self):
        record = self.env["eh.log.dashboard"].create({})
        self.assertTrue(record.id)

    def test_zero_baseline(self):
        # Fresh record: every count is a non-negative integer.
        record = self.env["eh.log.dashboard"].create({})
        for field_name in (
            "open_quotation_count",
            "open_freight_job_count",
            "in_transit_freight_count",
            "customs_declarations_open_count",
            "customs_declarations_rejected_count",
            "transport_trips_today_count",
            "deliveries_today_count",
            "cold_chain_deviations_count",
            "dangerous_goods_active_count",
            "containers_at_yard_count",
            "warehouse_open_receipts_count",
            "warehouse_open_picks_count",
            "carrier_bookings_active_count",
            "track_events_today_count",
            "edi_dead_letter_count",
            "port_calls_active_count",
            "project_cargo_jobs_executing_count",
            "permits_expiring_count",
        ):
            value = getattr(record, field_name)
            self.assertGreaterEqual(value, 0,
                                    f"{field_name} must be non-negative")

    def test_module_flag_for_present_engine_models(self):
        # The dashboard always runs against the engines, so freight
        # job model is present; the relevant counts are computable.
        record = self.env["eh.log.dashboard"].create({})
        Job = self.env["eh.log.freight.job"]
        baseline = Job.search_count([
            ("state", "=", "in_transit"),
        ])
        self.assertEqual(record.in_transit_freight_count, baseline)

    def test_action_open_dashboard_returns_act_window(self):
        action = self.env["eh.log.dashboard"].action_open_dashboard()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "eh.log.dashboard")
        self.assertEqual(action["view_mode"], "form")

    def test_drill_down_action_freight_in_transit(self):
        record = self.env["eh.log.dashboard"].create({})
        action = record.action_open_freight_in_transit()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "eh.log.freight.job")
        self.assertIn(("state", "=", "in_transit"), action["domain"])

    def test_module_flags_match_registry(self):
        record = self.env["eh.log.dashboard"].create({})
        # Last mile ships in the suite under tests; depending on the
        # test scope the model may or may not be present. The flag
        # must reflect reality either way.
        self.assertEqual(
            record.has_last_mile,
            bool(self.env.get("eh.log.last.mile.delivery")),
        )
        self.assertEqual(
            record.has_track_trace,
            bool(self.env.get("eh.log.track.event")),
        )
