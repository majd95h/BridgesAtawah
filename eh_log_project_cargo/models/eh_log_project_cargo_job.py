# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Project cargo job spine.

State machine:

    draft -> surveyed -> planned -> executing -> completed -> closed
                                              \-> cancelled

Direct writes to state are blocked. Each transition has an explicit
prerequisite check: surveyed requires at least one route survey,
planned requires a convoy with vehicle assignments, executing
requires all permits in valid state.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "draft":      ("surveyed", "cancelled"),
    "surveyed":   ("planned", "draft", "cancelled"),
    "planned":    ("executing", "surveyed", "cancelled"),
    "executing":  ("completed", "cancelled"),
    "completed":  ("closed",),
    "closed":     (),
    "cancelled":  (),
}


class EhLogProjectCargoJob(models.Model):
    _name = "eh.log.project.cargo.job"
    _description = "Project Cargo Job"
    _order = "create_date desc, id desc"
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
            ("draft", "Draft"),
            ("surveyed", "Surveyed"),
            ("planned", "Planned"),
            ("executing", "Executing"),
            ("completed", "Completed"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    customer_partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
    )
    customer_reference = fields.Char(string="Customer Reference", tracking=True)
    project_name = fields.Char(string="Project Name", tracking=True)
    origin_partner_id = fields.Many2one("res.partner", string="Origin")
    destination_partner_id = fields.Many2one("res.partner", string="Destination")
    target_start_date = fields.Date(string="Target Start", tracking=True)
    target_end_date = fields.Date(string="Target End", tracking=True)
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="set null",
    )
    item_ids = fields.One2many(
        "eh.log.project.cargo.item",
        "job_id",
        string="Items",
    )
    item_count = fields.Integer(
        string="Items",
        compute="_compute_item_count",
        store=True,
    )
    has_oversized_item = fields.Boolean(
        string="Has Oversized Item",
        compute="_compute_has_oversized_item",
        store=True,
        help=(
            "Computed: true when any item exceeds the configured oversize thresholds (length/width/height/weight). Triggers permit and route survey requirements."
        )
    )
    convoy_ids = fields.One2many(
        "eh.log.project.cargo.convoy",
        "job_id",
        string="Convoys",
    )
    convoy_count = fields.Integer(
        string="Convoys",
        compute="_compute_convoy_count",
    )
    permit_ids = fields.One2many(
        "eh.log.project.cargo.permit",
        "job_id",
        string="Permits",
    )
    permit_count = fields.Integer(
        string="Permits",
        compute="_compute_permit_count",
    )
    route_survey_ids = fields.One2many(
        "eh.log.project.cargo.route.survey",
        "job_id",
        string="Route Surveys",
    )
    method_statement = fields.Html(
        string="Method Statement",
        translate=False,
        help=(
            "Free-form method statement that prints on the Method "
            "Statement PDF. Operators write this once the survey "
            "and the lift plan are agreed."
        ),
    )
    lift_study_notes = fields.Html(
        string="Lift Study Notes",
        translate=False,
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
                    "eh.log.project.cargo.job"
                ) or _("New")
        return super().create(vals_list)

    @api.depends("item_ids")
    def _compute_item_count(self):
        for job in self:
            job.item_count = len(job.item_ids)

    @api.depends("item_ids.is_oversized")
    def _compute_has_oversized_item(self):
        for job in self:
            job.has_oversized_item = any(job.item_ids.mapped("is_oversized"))

    def _compute_convoy_count(self):
        for job in self:
            job.convoy_count = len(job.convoy_ids)

    def _compute_permit_count(self):
        for job in self:
            job.permit_count = len(job.permit_ids)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _assert_transition_allowed(self, target_state):
        """Raise JobStateConflictError when target_state is unreachable
        from the current state, so action methods can validate the state
        machine before they enforce business preconditions."""
        self.ensure_one()
        if target_state not in ALLOWED_TRANSITIONS.get(self.state, ()):
            raise JobStateConflictError(
                1,
                _("Project cargo job %(name)s cannot move from "
                  "%(from)s to %(to)s.") % {
                    "name": self.name,
                    "from": self.state,
                    "to": target_state,
                },
            )

    def _transition_state(self, target_state):
        for job in self:
            job._assert_transition_allowed(target_state)
            job.with_context(
                eh_log_project_cargo_internal_state_write=True
            ).write({"state": target_state})

    def action_mark_surveyed(self):
        for job in self:
            job._assert_transition_allowed("surveyed")
            if not job.route_survey_ids:
                raise UserError(_(
                    "[EHL-PCG-002] Job %(name)s cannot move to "
                    "Surveyed without at least one route survey."
                ) % {"name": job.name})
        self._transition_state("surveyed")

    def action_mark_planned(self):
        for job in self:
            job._assert_transition_allowed("planned")
            if not job.convoy_ids:
                raise UserError(_(
                    "[EHL-PCG-003] Job %(name)s cannot move to "
                    "Planned without at least one convoy."
                ) % {"name": job.name})
            for convoy in job.convoy_ids:
                if not convoy.vehicle_ids:
                    raise UserError(_(
                        "[EHL-PCG-004] Convoy %(name)s has no "
                        "vehicle assignments."
                    ) % {"name": convoy.name})
        self._transition_state("planned")

    def action_start_execution(self):
        for job in self:
            job._assert_transition_allowed("executing")
            invalid_permits = job.permit_ids.filtered(
                lambda p: p.state not in ("issued", "active")
            )
            if invalid_permits:
                raise UserError(_(
                    "[EHL-PCG-005] Job %(name)s has permits not in "
                    "issued / active state: %(permits)s"
                ) % {
                    "name": job.name,
                    "permits": ", ".join(invalid_permits.mapped("name")),
                })
        self._transition_state("executing")

    def action_mark_completed(self):
        self._transition_state("completed")

    def action_close(self):
        self._transition_state("closed")

    def action_cancel(self):
        self._transition_state("cancelled")

    def action_reset_to_draft(self):
        self._transition_state("draft")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_project_cargo_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-PCG-006] Project-cargo job state must change "
                "via the action buttons."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Stat-button targets
    # ------------------------------------------------------------------
    def action_view_convoys(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Convoys"),
            "res_model": "eh.log.project.cargo.convoy",
            "view_mode": "list,form",
            "domain": [("job_id", "=", self.id)],
            "context": {"default_job_id": self.id},
        }

    def action_view_permits(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Permits"),
            "res_model": "eh.log.project.cargo.permit",
            "view_mode": "list,form",
            "domain": [("job_id", "=", self.id)],
            "context": {"default_job_id": self.id},
        }
