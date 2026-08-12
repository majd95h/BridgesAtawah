# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Container M&R work order.

State machine: draft -> estimated -> approved -> in_progress -> completed
-> closed. Plus cancelled side branch from any pre-completed state.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


WO_STATES = [
    ("draft", "Draft"),
    ("estimated", "Estimated"),
    ("approved", "Approved"),
    ("in_progress", "In Progress"),
    ("completed", "Completed"),
    ("closed", "Closed"),
    ("cancelled", "Cancelled"),
]

ALLOWED_WO_TRANSITIONS = {
    "draft": {"estimated", "cancelled"},
    "estimated": {"approved", "draft", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


class EhLogContainerMgmtWorkOrder(models.Model):
    _name = "eh.log.container.mgmt.work.order"
    _description = "Container M&R Work Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _rec_names_search = ["name"]

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
        selection=WO_STATES,
        string="State",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    container_id = fields.Many2one(
        "eh.log.freight.container",
        string="Container",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    depot_id = fields.Many2one(
        "eh.log.container.mgmt.depot",
        string="Depot",
        required=True,
        ondelete="restrict",
        index=True,
    )

    trigger_movement_id = fields.Many2one(
        "eh.log.container.mgmt.movement",
        string="Trigger Movement",
        ondelete="set null",
        help="Movement (typically a damaged-on-arrival gate-in) that "
             "triggered the work order.",
    )

    fault_description = fields.Text(string="Fault Description", required=True)
    repair_summary = fields.Text(string="Repair Summary")

    line_ids = fields.One2many(
        "eh.log.container.mgmt.work.order.line",
        "work_order_id",
        string="Cost Lines",
        copy=True,
    )

    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
    )

    actual_cost = fields.Monetary(
        string="Actual Cost",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    estimated_at = fields.Datetime(string="Estimated At", readonly=True, copy=False, tracking=True)
    approved_at = fields.Datetime(string="Approved At", readonly=True, copy=False, tracking=True)
    approved_by_id = fields.Many2one("res.users", string="Approved By", readonly=True, copy=False)
    started_at = fields.Datetime(string="Started At", readonly=True, copy=False, tracking=True)
    completed_at = fields.Datetime(string="Completed At", readonly=True, copy=False, tracking=True)

    company_id = fields.Many2one(
        related="container_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("line_ids", "line_ids.estimated_amount", "line_ids.actual_amount")
    def _compute_costs(self):
        for record in self:
            record.estimated_cost = sum(record.line_ids.mapped("estimated_amount"))
            record.actual_cost = sum(record.line_ids.mapped("actual_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.container.mgmt.work.order"
                ) or _("New")
        return super().create(vals_list)

    def _transition_state(self, target_state: str):
        for record in self:
            current = record.state
            allowed = ALLOWED_WO_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    140,
                    _(
                        "M&R work order %(name)s cannot move from "
                        "%(current)s to %(target)s. Allowed transitions "
                        "from %(current)s: %(allowed)s."
                    ) % {
                        "name": record.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            record.with_context(eh_log_container_mgmt_wo_state_write=True).write({
                "state": target_state,
            })

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_container_mgmt_wo_state_write"):
            raise UserError(_(
                "[EHL-CTNR-WO-001] State changes on a work order must "
                "go through the action buttons. Direct writes are "
                "rejected."
            ))
        return super().write(vals)

    # ----- Actions -----

    def action_set_estimated(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_(
                    "[EHL-CTNR-WO-002] Work order %(name)s cannot move "
                    "to Estimated without at least one cost line."
                ) % {"name": record.name})
            record._transition_state("estimated")
            record.estimated_at = fields.Datetime.now()
        return True

    def action_approve(self):
        for record in self:
            if not self.env.su and not self.env.user.has_group(
                "eh_log_base.group_eh_log_manager"
            ):
                raise UserError(_(
                    "[EHL-CTNR-WO-003] Only logistics managers can "
                    "approve M&R work orders."
                ))
            record._transition_state("approved")
            record.approved_at = fields.Datetime.now()
            record.approved_by_id = self.env.user
        return True

    def action_start(self):
        self._transition_state("in_progress")
        for record in self:
            record.started_at = fields.Datetime.now()
        return True

    def action_complete(self):
        for record in self:
            for line in record.line_ids:
                if line.actual_amount <= 0:
                    raise UserError(_(
                        "[EHL-CTNR-WO-004] Cannot complete work order "
                        "%(name)s: line '%(line)s' has zero actual cost. "
                        "Capture actual costs before completion."
                    ) % {"name": record.name, "line": line.description})
            record._transition_state("completed")
            record.completed_at = fields.Datetime.now()
        return True

    def action_close(self):
        self._transition_state("closed")
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True

    def action_back_to_draft(self):
        self._transition_state("draft")
        return True
