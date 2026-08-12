# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Road transport trip.

Born from a confirmed sale order or attached to an existing freight
job for the road leg. Carries pickup and delivery locations,
vehicle and driver assignment, planned and actual datetimes, route
distance, and demurrage/detention computation.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


TRIP_STATES = [
    ("planned", "Planned"),
    ("dispatched", "Dispatched"),
    ("at_pickup", "At Pickup"),
    ("in_transit", "In Transit"),
    ("at_delivery", "At Delivery"),
    ("delivered", "Delivered"),
    ("closed", "Closed"),
    ("cancelled", "Cancelled"),
]

ALLOWED_TRIP_TRANSITIONS = {
    "planned": {"dispatched", "cancelled"},
    "dispatched": {"at_pickup", "in_transit", "cancelled"},
    "at_pickup": {"in_transit", "cancelled"},
    "in_transit": {"at_delivery", "cancelled"},
    "at_delivery": {"delivered", "cancelled"},
    "delivered": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


class EhLogTransportTrip(models.Model):
    _name = "eh.log.transport.trip"
    _description = "Transport Trip"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _order = "create_date desc, id desc"
    _rec_names_search = ["name", "customer_reference"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )

    state = fields.Selection(
        selection=TRIP_STATES,
        string="State",
        default="planned",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_transport_trip_company_rel",
        "trip_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    # ----- Source linkage -----

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="restrict",
        index=True,
        copy=False,
    )

    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
        ondelete="set null",
        index=True,
        copy=False,
    )

    # ----- Parties -----

    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        index=True,
        tracking=True,
    )

    customer_reference = fields.Char(string="Customer Reference", tracking=True)

    # ----- Route -----

    pickup_partner_id = fields.Many2one(
        "res.partner",
        string="Pickup Address",
        index=True,
        tracking=True,
    )

    pickup_location = fields.Char(string="Pickup Location")

    delivery_partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Address",
        index=True,
        tracking=True,
    )

    delivery_location = fields.Char(string="Delivery Location")

    distance_km = fields.Float(string="Distance (km)")

    # ----- Resources -----

    vehicle_id = fields.Many2one(
        "eh.log.transport.vehicle",
        string="Vehicle",
        index=True,
        tracking=True,
        help=(
            "Tractor unit assigned to the trip. Vehicle telematics events (gate-in, gate-out) bind to this record via the trackable mixin."
        )
    )

    trailer_id = fields.Many2one(
        "eh.log.transport.vehicle",
        string="Trailer",
        domain=[("vehicle_type", "in", ("trailer", "low_bed", "reefer", "tanker", "flatbed"))],
        index=True,
        tracking=True,
    )

    driver_id = fields.Many2one(
        "eh.log.transport.driver",
        string="Driver",
        index=True,
        tracking=True,
        help=(
            "Driver assigned. License expiry date is checked at dispatch; an expired licence raises a soft warning before the truck rolls."
        )
    )

    # ----- Dates -----

    pickup_planned_at = fields.Datetime(string="Planned Pickup", tracking=True)
    pickup_actual_at = fields.Datetime(string="Actual Pickup", tracking=True)
    delivery_planned_at = fields.Datetime(string="Planned Delivery", tracking=True)
    delivery_actual_at = fields.Datetime(string="Actual Delivery", tracking=True)

    # ----- Cargo -----

    cargo_description = fields.Text(string="Cargo Description")
    package_count = fields.Integer(string="Packages")
    gross_weight_kg = fields.Float(string="Gross Weight (kg)")

    # ----- Demurrage and detention -----

    free_time_hours = fields.Float(
        string="Free Time (hours)",
        default=4.0,
        help="Hours included in the agreed price before demurrage and "
             "detention starts to accrue.",
    )

    demurrage_rate_per_hour = fields.Monetary(
        string="Demurrage Rate (per hour)",
        currency_field="currency_id",
    )

    detention_hours = fields.Float(
        string="Detention (hours)",
        compute="_compute_detention",
        store=True,
        help="Total time at pickup and delivery beyond the free time. "
             "Computed when both ends have actual datetime stamped.",
    )

    detention_amount = fields.Monetary(
        string="Detention Amount",
        currency_field="currency_id",
        compute="_compute_detention",
        store=True,
    )

    # ----- ePOD -----

    pod_ids = fields.One2many(
        "eh.log.transport.pod",
        "trip_id",
        string="ePOD",
        copy=False,
    )

    pod_count = fields.Integer(
        string="ePODs",
        compute="_compute_pod_count",
    )

    # ----- Currency -----

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
        store=True,
    )

    notes = fields.Text(string="Notes")

    # ----- Computes -----

    @api.depends("company_id")
    def _compute_company_ids(self):
        for trip in self:
            trip.company_ids = trip.company_id

    @api.depends(
        "pickup_planned_at", "pickup_actual_at",
        "delivery_planned_at", "delivery_actual_at",
        "free_time_hours", "demurrage_rate_per_hour",
    )
    def _compute_detention(self):
        for trip in self:
            total_hours = 0.0
            if trip.pickup_planned_at and trip.pickup_actual_at:
                delta = trip.pickup_actual_at - trip.pickup_planned_at
                total_hours += max(0.0, delta.total_seconds() / 3600.0)
            if trip.delivery_planned_at and trip.delivery_actual_at:
                delta = trip.delivery_actual_at - trip.delivery_planned_at
                total_hours += max(0.0, delta.total_seconds() / 3600.0)
            chargeable = max(0.0, total_hours - (trip.free_time_hours or 0.0))
            trip.detention_hours = chargeable
            trip.detention_amount = chargeable * (trip.demurrage_rate_per_hour or 0.0)

    @api.depends("pod_ids")
    def _compute_pod_count(self):
        for trip in self:
            trip.pod_count = len(trip.pod_ids)

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.transport.trip"
                ) or _("New")
        return super().create(vals_list)

    # ----- State guards -----

    def _check_dispatch_prerequisites(self):
        for trip in self:
            blockers = []
            if not trip.vehicle_id:
                blockers.append(_("Vehicle is not assigned."))
            if not trip.driver_id:
                blockers.append(_("Driver is not assigned."))
            if trip.driver_id and trip.driver_id.is_license_expired:
                blockers.append(_(
                    "Driver %(driver)s has an expired license "
                    "(expired %(date)s). Renew or assign a different "
                    "driver."
                ) % {
                    "driver": trip.driver_id.name,
                    "date": trip.driver_id.license_expiry_date,
                })
            if not trip.pickup_planned_at:
                blockers.append(_("Planned pickup time is not set."))
            if not trip.delivery_planned_at:
                blockers.append(_("Planned delivery time is not set."))
            if blockers:
                raise UserError(_(
                    "[EHL-TRIP-001] Trip %(name)s cannot be dispatched. "
                    "Resolve the following:\n\n- %(list)s"
                ) % {
                    "name": trip.name,
                    "list": "\n- ".join(blockers),
                })

    def _transition_state(self, target_state: str):
        for trip in self:
            current = trip.state
            allowed = ALLOWED_TRIP_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    13,
                    _(
                        "Trip %(name)s cannot move from %(current)s to "
                        "%(target)s. Allowed transitions from "
                        "%(current)s: %(allowed)s."
                    ) % {
                        "name": trip.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            trip.with_context(eh_log_transport_internal_state_write=True).write({
                "state": target_state,
            })
            self.env["eh.log.event"].log(
                category="state_transition",
                summary=_("Trip %(name)s moved to %(state)s.") % {
                    "name": trip.name, "state": target_state,
                },
                related_model="eh.log.transport.trip",
                related_record_id=trip.id,
                related_record_display=trip.name,
                context={
                    "from_state": current,
                    "to_state": target_state,
                },
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_transport_internal_state_write"):
            raise UserError(_(
                "[EHL-TRIP-002] State changes on a trip must go "
                "through the action buttons. Direct writes are rejected."
            ))
        return super().write(vals)

    # ----- Actions -----

    def action_dispatch(self):
        self._check_dispatch_prerequisites()
        self._transition_state("dispatched")
        return True

    def action_set_at_pickup(self):
        self._transition_state("at_pickup")
        for trip in self:
            if not trip.pickup_actual_at:
                trip.pickup_actual_at = fields.Datetime.now()
        return True

    def action_set_in_transit(self):
        self._transition_state("in_transit")
        return True

    def action_set_at_delivery(self):
        self._transition_state("at_delivery")
        return True

    def action_set_delivered(self):
        self._transition_state("delivered")
        for trip in self:
            if not trip.delivery_actual_at:
                trip.delivery_actual_at = fields.Datetime.now()
        return True

    def action_close(self):
        self._transition_state("closed")
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True

    def action_view_pods(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ePOD"),
            "res_model": "eh.log.transport.pod",
            "view_mode": "list,form",
            "domain": [("trip_id", "=", self.id)],
            "context": {"default_trip_id": self.id},
        }
