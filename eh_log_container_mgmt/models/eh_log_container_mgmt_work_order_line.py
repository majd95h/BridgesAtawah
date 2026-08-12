# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Work order cost line: estimated and actual amounts per repair item."""
from odoo import _, api, fields, models


REPAIR_KINDS = [
    ("dent", "Dent / Bend"),
    ("hole", "Hole / Puncture"),
    ("door", "Door / Hinge"),
    ("seal", "Seal Replacement"),
    ("paint", "Paint / Marking"),
    ("flooring", "Flooring"),
    ("reefer_unit", "Reefer Unit"),
    ("inspection", "Inspection / Survey"),
    ("other", "Other"),
]


class EhLogContainerMgmtWorkOrderLine(models.Model):
    _name = "eh.log.container.mgmt.work.order.line"
    _description = "Work Order Cost Line"
    _order = "work_order_id, sequence, id"

    work_order_id = fields.Many2one(
        "eh.log.container.mgmt.work.order",
        string="Work Order",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sequence = fields.Integer(default=10)

    repair_kind = fields.Selection(
        selection=REPAIR_KINDS,
        string="Repair Kind",
        required=True,
        default="other",
        index=True,
    )

    description = fields.Char(
        string="Description",
        required=True,
        translate=True,
    )

    quantity = fields.Float(string="Quantity", default=1.0)

    estimated_unit_cost = fields.Monetary(
        string="Estimated Unit Cost",
        currency_field="currency_id",
    )

    estimated_amount = fields.Monetary(
        string="Estimated Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    actual_unit_cost = fields.Monetary(
        string="Actual Unit Cost",
        currency_field="currency_id",
    )

    actual_amount = fields.Monetary(
        string="Actual Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    currency_id = fields.Many2one(
        related="work_order_id.currency_id",
        store=True,
        readonly=True,
    )

    notes = fields.Char()

    @api.depends("quantity", "estimated_unit_cost", "actual_unit_cost")
    def _compute_amounts(self):
        for line in self:
            line.estimated_amount = (line.quantity or 0.0) * (line.estimated_unit_cost or 0.0)
            line.actual_amount = (line.quantity or 0.0) * (line.actual_unit_cost or 0.0)
