# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Outbound pick: state machine, line items, movement emission.

A pick is the outbound counterpart of a receipt. State machine:

    planned -> picking -> packed -> shipped -> closed

Each transition emits movements on the picking step and locks lines
on closed. Direct writes to state are blocked.

Picks are usually generated from a sale order line on the warehouse
3PL service product, or from an inbound pick request from a freight
job. Standalone picks are also supported for ad-hoc fulfilment.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "planned": ("picking", "cancelled"),
    "picking": ("packed", "cancelled"),
    "packed": ("shipped", "cancelled"),
    "shipped": ("closed",),
    "closed": (),
    "cancelled": (),
}


class EhLogWarehousePick(models.Model):
    _name = "eh.log.warehouse.pick"
    _description = "Warehouse Pick"
    _order = "planned_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name", "customer_reference"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("picking", "Picking"),
            ("packed", "Packed"),
            ("shipped", "Shipped"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="planned",
        tracking=True,
        copy=False,
    )
    client_id = fields.Many2one(
        "eh.log.warehouse.client",
        string="3PL Client",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    facility_id = fields.Many2one(
        "eh.log.warehouse.facility",
        string="Facility",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Ship-To Customer",
        tracking=True,
    )
    customer_reference = fields.Char(
        string="Customer Reference",
        tracking=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="set null",
        help=(
            "Source sale order if the pick was spawned from a "
            "warehouse 3PL service line; standalone picks leave "
            "this empty."
        ),
    )
    planned_date = fields.Date(
        string="Planned Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    picking_started_at = fields.Datetime(
        string="Picking Started At",
        readonly=True,
        copy=False,
    )
    shipped_at = fields.Datetime(
        string="Shipped At",
        readonly=True,
        copy=False,
    )
    closed_at = fields.Datetime(
        string="Closed At",
        readonly=True,
        copy=False,
    )
    line_ids = fields.One2many(
        "eh.log.warehouse.pick.line",
        "pick_id",
        string="Lines",
        copy=True,
    )
    pallet_count = fields.Integer(
        string="Pallets",
        compute="_compute_pallet_count",
        store=True,
    )
    pick_line_count = fields.Integer(
        string="Pick Lines",
        compute="_compute_pick_line_count",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.warehouse.pick"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("line_ids.pallet_count")
    def _compute_pallet_count(self):
        for pick in self:
            pick.pallet_count = sum(pick.line_ids.mapped("pallet_count"))

    @api.depends("line_ids")
    def _compute_pick_line_count(self):
        for pick in self:
            pick.pick_line_count = len(pick.line_ids)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for pick in self:
            current = pick.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Pick %(name)s cannot move from %(from)s to "
                      "%(to)s. Allowed: %(allowed)s.") % {
                        "name": pick.name,
                        "from": current,
                        "to": target_state,
                        "allowed": ", ".join(allowed) or _("none"),
                    },
                )
            pick.with_context(
                eh_log_warehouse_internal_state_write=True
            ).write({"state": target_state})

    def action_start_picking(self):
        for pick in self:
            if not pick.line_ids:
                raise UserError(_(
                    "[EHL-WHS-012] Pick %(name)s has no lines."
                ) % {"name": pick.name})
            for line in pick.line_ids:
                if not line.source_location_id:
                    raise UserError(_(
                        "[EHL-WHS-013] Pick line for %(product)s "
                        "has no source location."
                    ) % {"product": line.product_id.display_name})
        self._transition_state("picking")
        for pick in self:
            pick.picking_started_at = fields.Datetime.now()
            pick._emit_pick_movements()

    def action_mark_packed(self):
        self._transition_state("packed")

    def action_mark_shipped(self):
        self._transition_state("shipped")
        for pick in self:
            pick.shipped_at = fields.Datetime.now()

    def action_close(self):
        self._transition_state("closed")
        for pick in self:
            pick.closed_at = fields.Datetime.now()

    def action_cancel(self):
        self._transition_state("cancelled")

    def _emit_pick_movements(self):
        Movement = self.env["eh.log.warehouse.movement"].with_context(
            eh_log_warehouse_internal_movement=True,
        )
        for pick in self:
            for line in pick.line_ids:
                Movement.create({
                    "movement_type": "pick",
                    "client_id": pick.client_id.id,
                    "facility_id": pick.facility_id.id,
                    "source_location_id": line.source_location_id.id,
                    "product_id": line.product_id.id,
                    "lot_reference": line.lot_reference or "",
                    "quantity": line.quantity,
                    "pallet_count": line.pallet_count,
                    "pick_id": pick.id,
                    "occurred_at": fields.Datetime.now(),
                    "company_id": pick.company_id.id,
                })

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_warehouse_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-WHS-007] Pick state must be changed via the "
                "action buttons, not by direct write."
            ))
        return super().write(vals)


class EhLogWarehousePickLine(models.Model):
    _name = "eh.log.warehouse.pick.line"
    _description = "Warehouse Pick Line"
    _order = "pick_id, sequence, id"

    pick_id = fields.Many2one(
        "eh.log.warehouse.pick",
        string="Pick",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        ondelete="restrict",
    )
    lot_reference = fields.Char(string="Lot / Batch")
    quantity = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
    )
    pallet_count = fields.Integer(
        string="Pallets",
        required=True,
        default=1,
    )
    source_location_id = fields.Many2one(
        "eh.log.warehouse.location",
        string="Source",
        ondelete="restrict",
        help=(
            "Where this line is picked from. Required before the "
            "picking action runs; planning may use a "
            "soon-to-be-resolved location."
        ),
    )
    company_id = fields.Many2one(
        related="pick_id.company_id",
        store=True,
        index=True,
    )

    def write(self, vals):
        for line in self:
            if line.pick_id.state in ("closed", "cancelled"):
                raise UserError(_(
                    "[EHL-WHS-009] Pick %(name)s is %(state)s; "
                    "lines are read-only."
                ) % {
                    "name": line.pick_id.name,
                    "state": line.pick_id.state,
                })
        return super().write(vals)
