# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Inbound receipt: state machine, line items, movement emission.

A receipt is the inbound counterpart of a pick. State machine:

    expected -> arrived -> inspecting -> putaway -> closed

Each transition emits a movement on the put-away step (closed state
also locks the lines). Direct writes to state are blocked. Lines
carry SKU, lot, expiry, pallet count.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


# Closed-form state transition table. Documented here so the
# operations team can reason about what is reachable from where
# without reading the action methods.
ALLOWED_TRANSITIONS = {
    "expected": ("arrived", "cancelled"),
    "arrived": ("inspecting", "cancelled"),
    "inspecting": ("putaway", "cancelled"),
    "putaway": ("closed",),
    "closed": (),
    "cancelled": (),
}


class EhLogWarehouseReceipt(models.Model):
    _name = "eh.log.warehouse.receipt"
    _description = "Warehouse Receipt"
    _order = "expected_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name", "supplier_reference"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [
            ("expected", "Expected"),
            ("arrived", "Arrived"),
            ("inspecting", "Inspecting"),
            ("putaway", "Putaway"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="expected",
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
    supplier_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        tracking=True,
        help=(
            "Supplier who shipped the goods. The receipt reconciles this party against the PO when the freight job is linked."
        )
    )
    supplier_reference = fields.Char(
        string="Supplier Reference",
        tracking=True,
    )
    expected_date = fields.Date(
        string="Expected Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help=(
            "Date the receipt is expected to arrive. Drives the dock scheduling list view and the late-arrival alerts."
        )
    )
    arrived_at = fields.Datetime(
        string="Arrived At",
        readonly=True,
        copy=False,
    )
    putaway_at = fields.Datetime(
        string="Putaway At",
        readonly=True,
        copy=False,
    )
    closed_at = fields.Datetime(
        string="Closed At",
        readonly=True,
        copy=False,
    )
    line_ids = fields.One2many(
        "eh.log.warehouse.receipt.line",
        "receipt_id",
        string="Lines",
        copy=True,
    )
    pallet_count = fields.Integer(
        string="Pallets",
        compute="_compute_pallet_count",
        store=True,
        help=(
            "Pallet count for storage billing. The snapshot table records this per day for storage charge computation."
        )
    )
    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
        ondelete="set null",
        help=(
            "Linked freight job when the receipt is the destination "
            "of an inbound shipment. Optional; standalone receipts "
            "for direct supplier deliveries leave it empty."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # ------------------------------------------------------------------
    # Defaults / sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.warehouse.receipt"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("line_ids.pallet_count")
    def _compute_pallet_count(self):
        for receipt in self:
            receipt.pallet_count = sum(receipt.line_ids.mapped("pallet_count"))

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for receipt in self:
            current = receipt.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Receipt %(name)s cannot move from %(from)s "
                      "to %(to)s. Allowed: %(allowed)s.") % {
                        "name": receipt.name,
                        "from": current,
                        "to": target_state,
                        "allowed": ", ".join(allowed) or _("none"),
                    },
                )
            receipt.with_context(
                eh_log_warehouse_internal_state_write=True
            ).write({"state": target_state})

    def action_mark_arrived(self):
        self._transition_state("arrived")
        for receipt in self:
            receipt.arrived_at = fields.Datetime.now()

    def action_start_inspection(self):
        self._transition_state("inspecting")

    def action_complete_putaway(self):
        for receipt in self:
            if not receipt.line_ids:
                raise UserError(_(
                    "[EHL-WHS-010] Receipt %(name)s has no lines; "
                    "add lines before completing put-away."
                ) % {"name": receipt.name})
            for line in receipt.line_ids:
                if not line.destination_location_id:
                    raise UserError(_(
                        "[EHL-WHS-011] Receipt line for product "
                        "%(product)s has no destination location."
                    ) % {"product": line.product_id.display_name})
        self._transition_state("putaway")
        for receipt in self:
            receipt.putaway_at = fields.Datetime.now()
            receipt._emit_putaway_movements()

    def action_close(self):
        self._transition_state("closed")
        for receipt in self:
            receipt.closed_at = fields.Datetime.now()

    def action_cancel(self):
        self._transition_state("cancelled")

    def _emit_putaway_movements(self):
        Movement = self.env["eh.log.warehouse.movement"].with_context(
            eh_log_warehouse_internal_movement=True,
        )
        for receipt in self:
            for line in receipt.line_ids:
                Movement.create({
                    "movement_type": "receipt",
                    "client_id": receipt.client_id.id,
                    "facility_id": receipt.facility_id.id,
                    "destination_location_id": line.destination_location_id.id,
                    "product_id": line.product_id.id,
                    "lot_reference": line.lot_reference or "",
                    "quantity": line.quantity,
                    "pallet_count": line.pallet_count,
                    "receipt_id": receipt.id,
                    "occurred_at": fields.Datetime.now(),
                    "company_id": receipt.company_id.id,
                })

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_warehouse_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-WHS-007] Receipt state must be changed via "
                "the action buttons, not by direct write."
            ))
        return super().write(vals)


class EhLogWarehouseReceiptLine(models.Model):
    _name = "eh.log.warehouse.receipt.line"
    _description = "Warehouse Receipt Line"
    _order = "receipt_id, sequence, id"

    receipt_id = fields.Many2one(
        "eh.log.warehouse.receipt",
        string="Receipt",
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
    expiry_date = fields.Date(string="Expiry Date")
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
    destination_location_id = fields.Many2one(
        "eh.log.warehouse.location",
        string="Destination",
        ondelete="restrict",
        help=(
            "Where this line will be put away. Required before the "
            "put-away action runs; until then, leaving it blank is "
            "allowed so the receipt can be created from the "
            "supplier ASN before the storage plan is finalised."
        ),
    )
    company_id = fields.Many2one(
        related="receipt_id.company_id",
        store=True,
        index=True,
    )

    def write(self, vals):
        for line in self:
            if line.receipt_id.state in ("closed", "cancelled"):
                raise UserError(_(
                    "[EHL-WHS-008] Receipt %(name)s is %(state)s; "
                    "lines are read-only."
                ) % {
                    "name": line.receipt_id.name,
                    "state": line.receipt_id.state,
                })
        return super().write(vals)
