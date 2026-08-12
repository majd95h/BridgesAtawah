# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Gate movement event.

Append-only at the API layer. The movement log is the canonical
history for an Equipment Interchange Receipt and for the demurrage
and detention computation.

Sequence on create. Container's last-known depot is updated by an
event hook in the freight container extension below.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


MOVEMENT_KINDS = [
    ("gate_in", "Gate-In (received)"),
    ("gate_out", "Gate-Out (released)"),
    ("transfer_in", "Transfer In (depot to depot)"),
    ("transfer_out", "Transfer Out (depot to depot)"),
    ("survey", "Survey"),
    ("repair_in", "Repair In"),
    ("repair_out", "Repair Out"),
]


class EhLogContainerMgmtMovement(models.Model):
    _name = "eh.log.container.mgmt.movement"
    _description = "Container Gate Movement"
    _order = "happened_at desc, id desc"
    _rec_names_search = ["name", "container_id"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
    )

    container_id = fields.Many2one(
        "eh.log.freight.container",
        string="Container",
        required=True,
        ondelete="restrict",
        index=True,
    )

    container_number = fields.Char(
        related="container_id.container_number",
        store=True,
        index=True,
        readonly=True,
    )

    movement_kind = fields.Selection(
        selection=MOVEMENT_KINDS,
        string="Kind",
        required=True,
        index=True,
    )

    depot_id = fields.Many2one(
        "eh.log.container.mgmt.depot",
        string="Depot",
        required=True,
        ondelete="restrict",
        index=True,
    )

    counterparty_depot_id = fields.Many2one(
        "eh.log.container.mgmt.depot",
        string="Counterparty Depot",
        ondelete="restrict",
        help="Source depot on a transfer-in, destination depot on "
             "a transfer-out. Empty for gate-in / gate-out at a single "
             "depot.",
    )

    happened_at = fields.Datetime(
        string="Happened At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )

    gate_operator_name = fields.Char(string="Gate Operator")

    seal_number = fields.Char(string="Seal Number")

    condition_note = fields.Text(
        string="Condition Note",
        help="Photographs and damage notes captured at the gate. "
             "Drives the M&R work order if a repair is needed.",
    )

    needs_repair = fields.Boolean(
        string="Needs Repair",
        help="Set at gate-in when the container is received with "
             "visible damage. Triggers a draft M&R work order on save.",
    )

    company_id = fields.Many2one(
        related="container_id.company_id",
        store=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.container.mgmt.movement"
                ) or _("New")
        records = super().create(vals_list)
        # Auto-spawn a draft work order for any movement flagged
        # needs_repair. The operator promotes it to estimated and
        # approves cost lines via the M&R workflow.
        WorkOrder = self.env["eh.log.container.mgmt.work.order"].sudo()
        for record in records:
            if record.needs_repair:
                WorkOrder.create({
                    "container_id": record.container_id.id,
                    "depot_id": record.depot_id.id,
                    "trigger_movement_id": record.id,
                    "fault_description": record.condition_note or _("Damage observed at gate."),
                })
        return records

    def write(self, vals):
        if not self.env.context.get("eh_log_container_mgmt_internal_movement_write"):
            forbidden = set(vals) - {"condition_note", "gate_operator_name", "seal_number"}
            if forbidden:
                raise UserError(_(
                    "[EHL-CTNR-MOV-001] Container movements are "
                    "append-only. The following fields cannot be edited "
                    "after capture: %(fields)s. Cancel the movement and "
                    "create a corrected one if a fix is required."
                ) % {"fields": ", ".join(sorted(forbidden))})
        return super().write(vals)
