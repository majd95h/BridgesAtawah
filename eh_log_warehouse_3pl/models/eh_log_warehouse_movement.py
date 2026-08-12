# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Append-only movement log.

Every billable handling activity lands here. The billing engine reads
this table; nothing else is the source of truth for handling charges.
The pallets-on-hand compute on locations also reads this table.

Movements are created exclusively through the put-away path on
receipts, the picking path on picks, the explicit transfer wizard
(internal), and the adjustment workflow. Direct ORM creates are
blocked: the context flag eh_log_warehouse_internal_movement is the
only way through.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Locked once a movement row exists. The notes column stays mutable
# so an operator can annotate a historical movement after the fact.
LOCKED_FIELDS = (
    "movement_type",
    "client_id",
    "facility_id",
    "source_location_id",
    "destination_location_id",
    "product_id",
    "lot_reference",
    "quantity",
    "pallet_count",
    "occurred_at",
    "receipt_id",
    "pick_id",
    "company_id",
)


class EhLogWarehouseMovement(models.Model):
    _name = "eh.log.warehouse.movement"
    _description = "Warehouse Movement"
    _order = "occurred_at desc, id desc"

    movement_type = fields.Selection(
        [
            ("receipt", "Receipt"),
            ("pick", "Pick"),
            ("transfer", "Internal Transfer"),
            ("adjustment_in", "Adjustment In"),
            ("adjustment_out", "Adjustment Out"),
        ],
        string="Type",
        required=True,
        index=True,
    )
    client_id = fields.Many2one(
        "eh.log.warehouse.client",
        string="3PL Client",
        required=True,
        ondelete="restrict",
        index=True,
    )
    facility_id = fields.Many2one(
        "eh.log.warehouse.facility",
        string="Facility",
        required=True,
        ondelete="restrict",
        index=True,
    )
    source_location_id = fields.Many2one(
        "eh.log.warehouse.location",
        string="Source Location",
        ondelete="restrict",
        index=True,
    )
    destination_location_id = fields.Many2one(
        "eh.log.warehouse.location",
        string="Destination Location",
        ondelete="restrict",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        ondelete="restrict",
        index=True,
    )
    lot_reference = fields.Char(string="Lot / Batch")
    quantity = fields.Float(string="Quantity", required=True)
    pallet_count = fields.Integer(string="Pallets", required=True, default=1)
    occurred_at = fields.Datetime(
        string="Occurred At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    receipt_id = fields.Many2one(
        "eh.log.warehouse.receipt",
        string="Source Receipt",
        ondelete="set null",
    )
    pick_id = fields.Many2one(
        "eh.log.warehouse.pick",
        string="Source Pick",
        ondelete="set null",
    )
    notes = fields.Text(string="Operator Notes")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_warehouse_internal_movement"):
            raise UserError(_(
                "[EHL-WHS-014] Warehouse movements must be created "
                "through receipt put-away, pick picking, transfer "
                "wizard, or adjustment workflow."
            ))
        return super().create(vals_list)

    def write(self, vals):
        locked = set(LOCKED_FIELDS) & set(vals.keys())
        if locked:
            raise UserError(_(
                "[EHL-WHS-015] Movement field(s) %(fields)s are "
                "immutable after creation. Post a reversing "
                "adjustment instead."
            ) % {"fields": ", ".join(sorted(locked))})
        return super().write(vals)

    def unlink(self):
        if self:
            raise UserError(_(
                "[EHL-WHS-016] Warehouse movements are append-only "
                "and cannot be deleted."
            ))
        return super().unlink()
