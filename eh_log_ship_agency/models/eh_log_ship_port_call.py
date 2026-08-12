# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Port call lifecycle.

A port call is one vessel attendance at one port. State machine:

    expected -> arrived -> berthed -> working -> sailed -> closed

Each transition stamps its time field automatically and emits a
Statement of Facts event so the SOF is built up as a side-effect of
normal operational actions, not as a parallel data-entry chore.

Berth assignment is sanity-checked: a vessel that exceeds the
berth's depth or LOA fails the move-to-berthed action with a clear
message rather than silently corrupting the call.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "expected":   ("arrived", "cancelled"),
    "arrived":    ("berthed", "sailed", "cancelled"),
    "berthed":    ("working", "sailed"),
    "working":    ("sailed",),
    "sailed":     ("closed",),
    "closed":     (),
    "cancelled":  (),
}


class EhLogShipPortCall(models.Model):
    _name = "eh.log.ship.port.call"
    _description = "Port Call"
    _order = "eta_at desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name", "voyage_reference"]

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
            ("berthed", "Berthed"),
            ("working", "Working"),
            ("sailed", "Sailed"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="expected",
        tracking=True,
        copy=False,
    )
    vessel_id = fields.Many2one(
        "eh.log.ship.vessel",
        string="Vessel",
        required=True,
        ondelete="restrict",
        tracking=True,
        help=(
            "Vessel making the call. Vessel master record carries the IMO number, flag, dimensions, and ownership for port and berth eligibility checks."
        )
    )
    voyage_reference = fields.Char(string="Voyage", tracking=True)
    port_partner_id = fields.Many2one(
        "res.partner",
        string="Port",
        required=True,
        tracking=True,
        domain="[('is_company', '=', True)]",
    )
    berth_id = fields.Many2one(
        "eh.log.ship.berth",
        string="Berth",
        ondelete="restrict",
        tracking=True,
        help=(
            "Optional until the vessel berths. Berth assignment "
            "validates draft and LOA against the berth dimensions."
        ),
    )
    principal_partner_id = fields.Many2one(
        "res.partner",
        string="Principal",
        required=True,
        tracking=True,
        help=(
            "The party the agent represents and bills for the call. "
            "Usually the operator from the vessel master, but may be "
            "the charterer for a voyage charter."
        ),
    )
    eta_at = fields.Datetime(string="ETA", tracking=True)
    arrived_at = fields.Datetime(string="Arrived At", readonly=True)
    nor_tendered_at = fields.Datetime(
        string="NOR Tendered At",
        tracking=True,
        help=(
            "Time the Notice of Readiness was tendered. Drives "
            "laytime calculation; must fall between arrived and "
            "berthed for the standard rules to apply."
        ),
    )
    berthed_at = fields.Datetime(string="Berthed At", readonly=True)
    working_at = fields.Datetime(string="Started Working At", readonly=True)
    sailed_at = fields.Datetime(string="Sailed At", readonly=True)
    closed_at = fields.Datetime(string="Closed At", readonly=True)
    sof_event_ids = fields.One2many(
        "eh.log.ship.sof.event",
        "port_call_id",
        string="SOF Events",
    )
    sof_event_count = fields.Integer(
        string="SOF Events",
        compute="_compute_sof_event_count",
    )
    disbursement_account_id = fields.Many2one(
        "eh.log.ship.disbursement.account",
        string="Disbursement Account",
        copy=False,
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
                    "eh.log.ship.port.call"
                ) or _("New")
        return super().create(vals_list)

    def _compute_sof_event_count(self):
        for call in self:
            call.sof_event_count = len(call.sof_event_ids)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for call in self:
            current = call.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Port call %(name)s cannot move from %(from)s "
                      "to %(to)s.") % {
                        "name": call.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            call.with_context(
                eh_log_ship_internal_state_write=True
            ).write({"state": target_state})
            call._log_sof(f"State: {target_state}")

    def action_mark_arrived(self):
        self._transition_state("arrived")
        for call in self:
            call.arrived_at = fields.Datetime.now()

    def action_assign_berth(self, berth=None):
        for call in self:
            target_berth = berth or call.berth_id
            if not target_berth:
                raise UserError(_(
                    "[EHL-SHP-005] Port call %(name)s has no berth "
                    "assigned; provide one before marking berthed."
                ) % {"name": call.name})
            problems = target_berth.check_compatibility(call.vessel_id)
            if problems:
                raise UserError(_(
                    "[EHL-SHP-006] Berth %(berth)s is not "
                    "compatible with vessel %(vessel)s: %(reasons)s"
                ) % {
                    "berth": target_berth.name,
                    "vessel": call.vessel_id.name,
                    "reasons": "; ".join(problems),
                })
            if berth and call.berth_id != berth:
                call.berth_id = berth
        self._transition_state("berthed")
        for call in self:
            call.berthed_at = fields.Datetime.now()

    def action_start_working(self):
        self._transition_state("working")
        for call in self:
            call.working_at = fields.Datetime.now()

    def action_mark_sailed(self):
        self._transition_state("sailed")
        for call in self:
            call.sailed_at = fields.Datetime.now()

    def action_close(self):
        for call in self:
            if call.disbursement_account_id and call.disbursement_account_id.state not in ("posted", "settled"):
                raise UserError(_(
                    "[EHL-SHP-007] Cannot close port call %(name)s "
                    "while the disbursement account is in state "
                    "%(state)s."
                ) % {
                    "name": call.name,
                    "state": call.disbursement_account_id.state,
                })
        self._transition_state("closed")
        for call in self:
            call.closed_at = fields.Datetime.now()

    def action_cancel(self):
        self._transition_state("cancelled")

    def action_tender_nor(self):
        for call in self:
            if call.state not in ("arrived", "berthed"):
                raise UserError(_(
                    "[EHL-SHP-008] NOR can only be tendered between "
                    "arrived and berthed states; current state is "
                    "%(state)s."
                ) % {"state": call.state})
            call.nor_tendered_at = fields.Datetime.now()
            call._log_sof("NOR tendered")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_ship_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-SHP-009] Port-call state must change via the "
                "action buttons."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log_sof(self, description, occurred_at=None):
        self.ensure_one()
        SOF = self.env["eh.log.ship.sof.event"].with_context(
            eh_log_ship_internal_sof_create=True,
        )
        SOF.create({
            "port_call_id": self.id,
            "description": description,
            "occurred_at": occurred_at or fields.Datetime.now(),
            "company_id": self.company_id.id,
        })

    def action_view_sof(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Statement of Facts"),
            "res_model": "eh.log.ship.sof.event",
            "view_mode": "list,form",
            "domain": [("port_call_id", "=", self.id)],
            "context": {"default_port_call_id": self.id},
        }

    def action_open_disbursement(self):
        self.ensure_one()
        DA = self.env["eh.log.ship.disbursement.account"]
        if self.disbursement_account_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "eh.log.ship.disbursement.account",
                "view_mode": "form",
                "res_id": self.disbursement_account_id.id,
                "target": "current",
            }
        account = DA.create({
            "port_call_id": self.id,
            "principal_partner_id": self.principal_partner_id.id,
            "company_id": self.company_id.id,
        })
        self.disbursement_account_id = account.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "eh.log.ship.disbursement.account",
            "view_mode": "form",
            "res_id": account.id,
            "target": "current",
        }
