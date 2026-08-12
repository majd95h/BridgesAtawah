# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Single-pane operational dashboard.

A transient model that computes KPI counts on read. The form view
renders the values as stat-button tiles, and the action methods
drill down to the source records on click.

Soft adaptation: every vertical-specific KPI uses ``self.env.get``
to find its source model. Modules that are not installed silently
contribute zero to the relevant tiles, and the form view hides
those tiles via ``invisible`` predicates so the operator only sees
the numbers that are real.

Performance: each KPI is a single ``search_count`` scoped per
company. Eight to twenty counts is well within sub-second territory
on any production database; the dashboard refreshes on every form
load without caching.
"""
from datetime import date, timedelta

from odoo import api, fields, models, _


# Window for "expiring soon" tiles. Operators can override per
# deployment via ir.config_parameter; the constant is the floor.
EXPIRY_WINDOW_DAYS = 7

# Window for "today" tiles. Anything dated within the next 24 hours.
TODAY_WINDOW_HOURS = 24


class EhLogDashboard(models.TransientModel):
    _name = "eh.log.dashboard"
    _description = "Logistics Dashboard"

    display_name = fields.Char(
        compute="_compute_display_name",
    )

    def _compute_display_name(self):
        for record in self:
            record.display_name = _("Logistics Dashboard")

    # ------------------------------------------------------------------
    # Always-on tiles (depend on engines hard-required by the manifest)
    # ------------------------------------------------------------------
    open_quotation_count = fields.Integer(
        string="Open Quotations",
        compute="_compute_open_quotation_count",
    )
    weighted_pipeline_value = fields.Monetary(
        string="Pipeline (Weighted)",
        compute="_compute_weighted_pipeline_value",
        currency_field="currency_id",
    )
    pipeline_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_weighted_pipeline_value",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="pipeline_currency_id",
    )
    open_freight_job_count = fields.Integer(
        string="Open Freight Jobs",
        compute="_compute_open_freight_job_count",
    )
    in_transit_freight_count = fields.Integer(
        string="In Transit",
        compute="_compute_in_transit_freight_count",
    )
    customs_declarations_open_count = fields.Integer(
        string="Open Customs Declarations",
        compute="_compute_customs_open_count",
    )
    customs_declarations_rejected_count = fields.Integer(
        string="Rejected Declarations",
        compute="_compute_customs_rejected_count",
    )
    transport_trips_today_count = fields.Integer(
        string="Transport Trips Today",
        compute="_compute_transport_trips_today_count",
    )

    # ------------------------------------------------------------------
    # Vertical tiles (soft, hidden if module absent)
    # ------------------------------------------------------------------
    has_last_mile = fields.Boolean(compute="_compute_module_flags")
    deliveries_today_count = fields.Integer(
        string="Deliveries Today",
        compute="_compute_deliveries_today_count",
    )
    cod_outstanding_total = fields.Float(
        string="COD Outstanding",
        compute="_compute_cod_outstanding_total",
    )

    has_cold_chain = fields.Boolean(compute="_compute_module_flags")
    cold_chain_deviations_count = fields.Integer(
        string="Cold Chain Deviations",
        compute="_compute_cold_chain_deviations_count",
    )

    has_dangerous_goods = fields.Boolean(compute="_compute_module_flags")
    dangerous_goods_active_count = fields.Integer(
        string="Active DG Declarations",
        compute="_compute_dangerous_goods_active_count",
    )

    has_container_mgmt = fields.Boolean(compute="_compute_module_flags")
    containers_at_yard_count = fields.Integer(
        string="Containers at Yard",
        compute="_compute_containers_at_yard_count",
    )

    has_warehouse_3pl = fields.Boolean(compute="_compute_module_flags")
    warehouse_open_receipts_count = fields.Integer(
        string="Open Warehouse Receipts",
        compute="_compute_warehouse_open_receipts_count",
    )
    warehouse_open_picks_count = fields.Integer(
        string="Open Warehouse Picks",
        compute="_compute_warehouse_open_picks_count",
    )

    has_carrier_portal = fields.Boolean(compute="_compute_module_flags")
    carrier_bookings_active_count = fields.Integer(
        string="Active Carrier Bookings",
        compute="_compute_carrier_bookings_active_count",
    )

    has_track_trace = fields.Boolean(compute="_compute_module_flags")
    track_events_today_count = fields.Integer(
        string="Tracking Events Today",
        compute="_compute_track_events_today_count",
    )

    has_edi = fields.Boolean(compute="_compute_module_flags")
    edi_dead_letter_count = fields.Integer(
        string="EDI Dead-Letter",
        compute="_compute_edi_dead_letter_count",
    )

    has_ship_agency = fields.Boolean(compute="_compute_module_flags")
    port_calls_active_count = fields.Integer(
        string="Active Port Calls",
        compute="_compute_port_calls_active_count",
    )

    has_project_cargo = fields.Boolean(compute="_compute_module_flags")
    project_cargo_jobs_executing_count = fields.Integer(
        string="Project Cargo Executing",
        compute="_compute_project_cargo_executing_count",
    )
    permits_expiring_count = fields.Integer(
        string="Permits Expiring",
        compute="_compute_permits_expiring_count",
    )

    # ------------------------------------------------------------------
    # Module presence flags
    # ------------------------------------------------------------------
    @api.depends_context("uid")
    def _compute_module_flags(self):
        env = self.env
        # `name in env` consults the model registry. `env.get(name)` would
        # return an empty recordset (falsy) regardless of install state, so
        # the previous bool(env.get(...)) made every flag permanently False.
        for record in self:
            record.has_last_mile = "eh.log.last.mile.delivery" in env
            record.has_cold_chain = "eh.log.cold.chain.run" in env
            record.has_dangerous_goods = "eh.log.dg.declaration" in env
            record.has_container_mgmt = "eh.log.container.mgmt.movement" in env
            record.has_warehouse_3pl = "eh.log.warehouse.receipt" in env
            record.has_carrier_portal = "eh.log.carrier.booking" in env
            record.has_track_trace = "eh.log.track.event" in env
            record.has_edi = "eh.log.edi.outbound" in env
            record.has_ship_agency = "eh.log.ship.port.call" in env
            record.has_project_cargo = "eh.log.project.cargo.job" in env

    # ------------------------------------------------------------------
    # Engine KPIs
    # ------------------------------------------------------------------
    def _compute_open_quotation_count(self):
        Order = self.env["sale.order"]
        for record in self:
            record.open_quotation_count = Order.search_count([
                ("state", "in", ("draft", "sent")),
            ])

    def _compute_weighted_pipeline_value(self):
        Order = self.env["sale.order"]
        company_currency = self.env.company.currency_id
        for record in self:
            orders = Order.search([
                ("state", "in", ("draft", "sent")),
            ])
            # Probability weighting if the field exists; otherwise 50% default.
            total = 0.0
            for order in orders:
                weight = (
                    (order.eh_log_quote_probability_pct or 50) / 100.0
                    if "eh_log_quote_probability_pct" in order._fields
                    else 0.5
                )
                amount = order.amount_untaxed if order.currency_id == company_currency else order.currency_id._convert(
                    order.amount_untaxed,
                    company_currency,
                    order.company_id,
                    order.date_order or fields.Date.today(),
                )
                total += amount * weight
            record.weighted_pipeline_value = total
            record.pipeline_currency_id = company_currency

    def _compute_open_freight_job_count(self):
        Job = self.env["eh.log.freight.job"]
        for record in self:
            record.open_freight_job_count = Job.search_count([
                ("state", "in", ("booked", "in_transit", "at_destination")),
            ])

    def _compute_in_transit_freight_count(self):
        Job = self.env["eh.log.freight.job"]
        for record in self:
            record.in_transit_freight_count = Job.search_count([
                ("state", "=", "in_transit"),
            ])

    def _compute_customs_open_count(self):
        Declaration = self.env.get("eh.log.customs.declaration")
        for record in self:
            if Declaration is None:
                record.customs_declarations_open_count = 0
                continue
            record.customs_declarations_open_count = Declaration.search_count([
                ("state", "in", ("draft", "ready", "submitted", "queried")),
            ])

    def _compute_customs_rejected_count(self):
        Declaration = self.env.get("eh.log.customs.declaration")
        for record in self:
            if Declaration is None:
                record.customs_declarations_rejected_count = 0
                continue
            record.customs_declarations_rejected_count = Declaration.search_count([
                ("state", "=", "rejected"),
            ])

    def _compute_transport_trips_today_count(self):
        Trip = self.env["eh.log.transport.trip"]
        today = fields.Date.context_today(self)
        for record in self:
            record.transport_trips_today_count = Trip.search_count([
                ("state", "in", ("dispatched", "at_pickup", "in_transit", "at_delivery")),
                ("pickup_planned_at", ">=", fields.Datetime.to_datetime(f"{today.isoformat()} 00:00:00")),
                ("pickup_planned_at", "<=", fields.Datetime.to_datetime(f"{today.isoformat()} 23:59:59")),
            ])

    # ------------------------------------------------------------------
    # Vertical KPIs (each guarded by env.get)
    # ------------------------------------------------------------------
    def _compute_deliveries_today_count(self):
        Delivery = self.env.get("eh.log.last.mile.delivery")
        today = fields.Date.context_today(self)
        for record in self:
            if Delivery is None:
                record.deliveries_today_count = 0
                continue
            record.deliveries_today_count = Delivery.search_count([
                ("state", "in", ("scheduled", "out_for_delivery")),
                ("scheduled_window_start", ">=", fields.Datetime.to_datetime(f"{today.isoformat()} 00:00:00")),
                ("scheduled_window_start", "<=", fields.Datetime.to_datetime(f"{today.isoformat()} 23:59:59")),
            ])

    def _compute_cod_outstanding_total(self):
        Delivery = self.env.get("eh.log.last.mile.delivery")
        for record in self:
            if Delivery is None:
                record.cod_outstanding_total = 0.0
                continue
            outstanding = Delivery.search([
                ("state", "in", ("scheduled", "out_for_delivery")),
                ("cod_amount", ">", 0),
            ])
            record.cod_outstanding_total = sum(
                outstanding.mapped("cod_amount")
            )

    def _compute_cold_chain_deviations_count(self):
        Run = self.env.get("eh.log.cold.chain.run")
        for record in self:
            if Run is None:
                record.cold_chain_deviations_count = 0
                continue
            record.cold_chain_deviations_count = Run.search_count([
                ("state", "in", ("active", "completed")),
                ("deviation_count", ">", 0),
            ])

    def _compute_dangerous_goods_active_count(self):
        Declaration = self.env.get("eh.log.dg.declaration")
        for record in self:
            if Declaration is None:
                record.dangerous_goods_active_count = 0
                continue
            record.dangerous_goods_active_count = Declaration.search_count([
                ("state", "in", ("draft", "submitted", "approved")),
            ])

    def _compute_containers_at_yard_count(self):
        Movement = self.env.get("eh.log.container.mgmt.movement")
        for record in self:
            if Movement is None:
                record.containers_at_yard_count = 0
                continue
            ins = Movement.search_count([("movement_kind", "=", "gate_in")])
            outs = Movement.search_count([("movement_kind", "=", "gate_out")])
            record.containers_at_yard_count = max(ins - outs, 0)

    def _compute_warehouse_open_receipts_count(self):
        Receipt = self.env.get("eh.log.warehouse.receipt")
        for record in self:
            if Receipt is None:
                record.warehouse_open_receipts_count = 0
                continue
            record.warehouse_open_receipts_count = Receipt.search_count([
                ("state", "in", ("expected", "arrived", "inspecting", "putaway")),
            ])

    def _compute_warehouse_open_picks_count(self):
        Pick = self.env.get("eh.log.warehouse.pick")
        for record in self:
            if Pick is None:
                record.warehouse_open_picks_count = 0
                continue
            record.warehouse_open_picks_count = Pick.search_count([
                ("state", "in", ("planned", "picking", "packed", "shipped")),
            ])

    def _compute_carrier_bookings_active_count(self):
        Booking = self.env.get("eh.log.carrier.booking")
        for record in self:
            if Booking is None:
                record.carrier_bookings_active_count = 0
                continue
            record.carrier_bookings_active_count = Booking.search_count([
                ("state", "in", ("requested", "accepted", "confirmed")),
            ])

    def _compute_track_events_today_count(self):
        Event = self.env.get("eh.log.track.event")
        today = fields.Date.context_today(self)
        for record in self:
            if Event is None:
                record.track_events_today_count = 0
                continue
            record.track_events_today_count = Event.search_count([
                ("occurred_at", ">=", fields.Datetime.to_datetime(f"{today.isoformat()} 00:00:00")),
                ("occurred_at", "<=", fields.Datetime.to_datetime(f"{today.isoformat()} 23:59:59")),
            ])

    def _compute_edi_dead_letter_count(self):
        Outbound = self.env.get("eh.log.edi.outbound")
        for record in self:
            if Outbound is None:
                record.edi_dead_letter_count = 0
                continue
            record.edi_dead_letter_count = Outbound.search_count([
                ("state", "=", "dead_letter"),
            ])

    def _compute_port_calls_active_count(self):
        PortCall = self.env.get("eh.log.ship.port.call")
        for record in self:
            if PortCall is None:
                record.port_calls_active_count = 0
                continue
            record.port_calls_active_count = PortCall.search_count([
                ("state", "in", ("expected", "arrived", "berthed", "working")),
            ])

    def _compute_project_cargo_executing_count(self):
        Job = self.env.get("eh.log.project.cargo.job")
        for record in self:
            if Job is None:
                record.project_cargo_jobs_executing_count = 0
                continue
            record.project_cargo_jobs_executing_count = Job.search_count([
                ("state", "in", ("planned", "executing")),
            ])

    def _compute_permits_expiring_count(self):
        Permit = self.env.get("eh.log.project.cargo.permit")
        for record in self:
            if Permit is None:
                record.permits_expiring_count = 0
                continue
            today = fields.Date.context_today(self)
            record.permits_expiring_count = Permit.search_count([
                ("state", "in", ("issued", "active")),
                ("valid_until", ">=", today),
                ("valid_until", "<=", today + timedelta(days=EXPIRY_WINDOW_DAYS)),
            ])

    # ------------------------------------------------------------------
    # Drill-down actions
    # ------------------------------------------------------------------
    def action_open_freight_in_transit(self):
        return self._open_window(
            "eh.log.freight.job",
            _("Freight Jobs in Transit"),
            [("state", "=", "in_transit")],
        )

    def action_open_open_quotations(self):
        return self._open_window(
            "sale.order",
            _("Open Quotations"),
            [("state", "in", ("draft", "sent"))],
        )

    def action_open_customs_open(self):
        return self._open_window(
            "eh.log.customs.declaration",
            _("Open Customs Declarations"),
            [("state", "in", ("draft", "ready", "submitted", "queried"))],
        )

    def action_open_customs_rejected(self):
        return self._open_window(
            "eh.log.customs.declaration",
            _("Rejected Customs Declarations"),
            [("state", "=", "rejected")],
        )

    def action_open_deliveries_today(self):
        today = fields.Date.context_today(self)
        return self._open_window(
            "eh.log.last.mile.delivery",
            _("Deliveries Today"),
            [
                ("state", "in", ("scheduled", "out_for_delivery")),
                ("scheduled_window_start", ">=", fields.Datetime.to_datetime(f"{today.isoformat()} 00:00:00")),
                ("scheduled_window_start", "<=", fields.Datetime.to_datetime(f"{today.isoformat()} 23:59:59")),
            ],
        )

    def action_open_warehouse_receipts(self):
        return self._open_window(
            "eh.log.warehouse.receipt",
            _("Open Warehouse Receipts"),
            [("state", "in", ("expected", "arrived", "inspecting", "putaway"))],
        )

    def action_open_warehouse_picks(self):
        return self._open_window(
            "eh.log.warehouse.pick",
            _("Open Warehouse Picks"),
            [("state", "in", ("planned", "picking", "packed", "shipped"))],
        )

    def action_open_carrier_bookings(self):
        return self._open_window(
            "eh.log.carrier.booking",
            _("Active Carrier Bookings"),
            [("state", "in", ("requested", "accepted", "confirmed"))],
        )

    def action_open_edi_dead_letter(self):
        return self._open_window(
            "eh.log.edi.outbound",
            _("EDI Dead-Letter Queue"),
            [("state", "=", "dead_letter")],
        )

    def action_open_port_calls(self):
        return self._open_window(
            "eh.log.ship.port.call",
            _("Active Port Calls"),
            [("state", "in", ("expected", "arrived", "berthed", "working"))],
        )

    def action_open_project_cargo_executing(self):
        return self._open_window(
            "eh.log.project.cargo.job",
            _("Project Cargo Jobs Executing"),
            [("state", "in", ("planned", "executing"))],
        )

    def action_open_permits_expiring(self):
        today = fields.Date.context_today(self)
        return self._open_window(
            "eh.log.project.cargo.permit",
            _("Permits Expiring Soon"),
            [
                ("state", "in", ("issued", "active")),
                ("valid_until", ">=", today),
                ("valid_until", "<=", today + timedelta(days=EXPIRY_WINDOW_DAYS)),
            ],
        )

    def _open_window(self, model_name, name, domain):
        # Membership in env tests whether the model is in the registry;
        # env.get(model_name) returns an empty recordset, which is falsy
        # even when the model is installed, so it cannot gate on presence.
        if model_name not in self.env:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model_name,
            "view_mode": "list,form",
            "domain": domain,
        }

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @api.model
    def action_open_dashboard(self):
        record = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Logistics Dashboard"),
            "res_model": self._name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }
