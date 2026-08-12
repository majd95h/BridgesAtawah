# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dispute spine + append-only event log.

State machine:

    opened -> investigating -> offered -> accepted -> settled -> closed
                                       \-> rejected -> escalated
                                                    \-> written_off

Direct writes to state are blocked; transitions advance through
explicit action methods. Each transition appends an event row.

Polymorphic source link: a dispute can be filed against a sale
order, freight job, transport trip, last-mile delivery, warehouse
receipt or pick, ship disbursement account, or container. The
allow-list is enforced at save time so a typo cannot create a
dangling pointer.

Financial fields (claimed / offered / settled amounts) are mutable
through the action methods only; the variance is computed and used
by the dashboard exposure tile.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


# Allow-list of polymorphic source models. The set is intentionally
# narrow; expanding it requires verifying that the model carries a
# customer / partner field the dispute can route notifications to.
ALLOWED_SOURCE_MODELS = {
    "sale.order",
    "eh.log.freight.job",
    "eh.log.transport.trip",
    "eh.log.last.mile.delivery",
    "eh.log.warehouse.receipt",
    "eh.log.warehouse.pick",
    "eh.log.ship.disbursement.account",
    "eh.log.freight.container",
}


ALLOWED_TRANSITIONS = {
    "opened":         ("investigating", "cancelled"),
    "investigating":  ("offered", "rejected", "escalated", "cancelled"),
    "offered":        ("accepted", "rejected", "escalated", "cancelled"),
    "accepted":       ("settled", "cancelled"),
    "settled":        ("closed",),
    "rejected":       ("escalated", "closed", "cancelled"),
    "escalated":      ("offered", "rejected", "written_off", "closed", "cancelled"),
    "written_off":    ("closed",),
    "closed":         (),
    "cancelled":      (),
}


# Locked fields on the event log; the notes field stays mutable.
EVENT_LOCKED_FIELDS = (
    "dispute_id",
    "event_type",
    "summary",
    "occurred_at",
    "from_state",
    "to_state",
    "company_id",
)


class EhLogDispute(models.Model):
    _name = "eh.log.dispute"
    _description = "Dispute"
    _order = "create_date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _rec_names_search = ["name", "subject"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    subject = fields.Char(string="Subject", required=True, tracking=True)
    description = fields.Text(string="Description")
    state = fields.Selection(
        [
            ("opened", "Opened"),
            ("investigating", "Investigating"),
            ("offered", "Offer Tendered"),
            ("accepted", "Offer Accepted"),
            ("settled", "Settled"),
            ("rejected", "Rejected"),
            ("escalated", "Escalated"),
            ("written_off", "Written Off"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="opened",
        tracking=True,
        copy=False,
    )
    category_id = fields.Many2one(
        "eh.log.dispute.category",
        string="Category",
        required=True,
        ondelete="restrict",
        tracking=True,
        help=(
            "Dispute category drives the SLA target and the routing to the responsible team. Categories ship as data; deployments can extend."
        )
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
    )
    res_model = fields.Char(
        string="Source Model",
        required=True,
        index=True,
    )
    res_id = fields.Integer(
        string="Source ID",
        required=True,
        index=True,
    )
    source_display = fields.Char(
        string="Source",
        compute="_compute_source_display",
        store=True,
    )
    opened_at = fields.Datetime(
        string="Opened At",
        default=fields.Datetime.now,
        required=True,
    )
    sla_target_date = fields.Date(
        string="SLA Target",
        compute="_compute_sla_target_date",
        store=True,
    )
    is_overdue = fields.Boolean(
        string="Overdue",
        compute="_compute_is_overdue",
        store=False,
    )
    claimed_amount = fields.Monetary(
        string="Claimed",
        currency_field="currency_id",
        help=(
            "Amount the customer is claiming. Compared with the offered amount to compute the negotiation gap on settlement."
        )
    )
    offered_amount = fields.Monetary(
        string="Offered",
        currency_field="currency_id",
    )
    settled_amount = fields.Monetary(
        string="Settled",
        currency_field="currency_id",
    )
    exposure = fields.Monetary(
        string="Open Exposure",
        compute="_compute_exposure",
        store=True,
        currency_field="currency_id",
        help=(
            "Settled amount once paid; otherwise the offered "
            "amount; otherwise the claimed amount. The dashboard "
            "uses this for the open-exposure tile."
        ),
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    survey_attached = fields.Boolean(
        string="Survey Attached",
        compute="_compute_survey_attached",
    )
    event_ids = fields.One2many(
        "eh.log.dispute.event",
        "dispute_id",
        string="Event Log",
    )
    event_count = fields.Integer(
        string="Events",
        compute="_compute_event_count",
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
                    "eh.log.dispute"
                ) or _("New")
        records = super().create(vals_list)
        for record in records:
            record._log_event("opened", "Dispute opened.")
        return records

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("res_model", "res_id")
    def _compute_source_display(self):
        for dispute in self:
            if not dispute.res_model or not dispute.res_id:
                dispute.source_display = ""
                continue
            Model = self.env.get(dispute.res_model)
            if Model is None:
                dispute.source_display = (
                    f"{dispute.res_model}/{dispute.res_id}"
                )
                continue
            record = Model.browse(dispute.res_id).exists()
            dispute.source_display = (
                record.display_name if record else f"{dispute.res_model}/{dispute.res_id}"
            )

    @api.depends("opened_at", "category_id.default_sla_days")
    def _compute_sla_target_date(self):
        for dispute in self:
            if not dispute.opened_at or not dispute.category_id:
                dispute.sla_target_date = False
                continue
            dispute.sla_target_date = (
                dispute.opened_at.date()
                + timedelta(days=dispute.category_id.default_sla_days or 0)
            )

    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        terminal = ("settled", "closed", "cancelled", "written_off")
        for dispute in self:
            dispute.is_overdue = bool(
                dispute.sla_target_date
                and dispute.sla_target_date < today
                and dispute.state not in terminal
            )

    @api.depends("claimed_amount", "offered_amount", "settled_amount", "state")
    def _compute_exposure(self):
        for dispute in self:
            if dispute.state == "settled":
                dispute.exposure = dispute.settled_amount
            elif dispute.offered_amount:
                dispute.exposure = dispute.offered_amount
            else:
                dispute.exposure = dispute.claimed_amount

    def _compute_survey_attached(self):
        Attachment = self.env["ir.attachment"]
        for dispute in self:
            dispute.survey_attached = bool(Attachment.search_count([
                ("res_model", "=", self._name),
                ("res_id", "=", dispute.id),
                ("name", "ilike", "survey"),
            ]))

    def _compute_event_count(self):
        for dispute in self:
            dispute.event_count = len(dispute.event_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("res_model")
    def _check_res_model_allowed(self):
        for dispute in self:
            if dispute.res_model not in ALLOWED_SOURCE_MODELS:
                raise ValidationError(_(
                    "[EHL-DSP-003] Source model %(model)s is not "
                    "in the dispute allow-list. Permitted: %(list)s"
                ) % {
                    "model": dispute.res_model,
                    "list": ", ".join(sorted(ALLOWED_SOURCE_MODELS)),
                })

    @api.constrains("res_model", "res_id")
    def _check_source_record_exists(self):
        for dispute in self:
            Model = self.env.get(dispute.res_model)
            if Model is None:
                continue
            if not Model.browse(dispute.res_id).exists():
                raise ValidationError(_(
                    "[EHL-DSP-004] Source record %(model)s/%(id)s "
                    "does not exist."
                ) % {
                    "model": dispute.res_model,
                    "id": dispute.res_id,
                })

    @api.constrains("offered_amount", "claimed_amount")
    def _check_offered_within_claim(self):
        for dispute in self:
            if (dispute.offered_amount and dispute.claimed_amount
                    and dispute.offered_amount > dispute.claimed_amount):
                raise ValidationError(_(
                    "[EHL-DSP-005] Offered amount %(offered)s "
                    "exceeds claimed amount %(claimed)s for dispute "
                    "%(name)s."
                ) % {
                    "offered": dispute.offered_amount,
                    "claimed": dispute.claimed_amount,
                    "name": dispute.name,
                })

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _assert_transition_allowed(self, target_state):
        """Raise JobStateConflictError if target_state is not reachable
        from the dispute's current state. Lets action methods validate the
        state machine before they mutate any other field."""
        self.ensure_one()
        if target_state not in ALLOWED_TRANSITIONS.get(self.state, ()):
            raise JobStateConflictError(
                1,
                _("Dispute %(name)s cannot move from %(from)s "
                  "to %(to)s.") % {
                    "name": self.name,
                    "from": self.state,
                    "to": target_state,
                },
            )

    def _transition_state(self, target_state, summary):
        for dispute in self:
            current = dispute.state
            dispute._assert_transition_allowed(target_state)
            dispute.with_context(
                eh_log_dispute_internal_state_write=True
            ).write({"state": target_state})
            dispute._log_event(
                "state_change", summary,
                from_state=current, to_state=target_state,
            )

    def action_start_investigation(self):
        self._transition_state("investigating", _("Investigation started."))

    def action_make_offer(self, amount=None):
        for dispute in self:
            if amount is not None:
                dispute.offered_amount = amount
            if not dispute.offered_amount:
                raise UserError(_(
                    "[EHL-DSP-006] Cannot tender an offer for "
                    "dispute %(name)s without an offered amount."
                ) % {"name": dispute.name})
        self._transition_state("offered", _("Offer tendered."))

    def action_accept_offer(self):
        self._transition_state("accepted", _("Offer accepted."))

    def action_reject(self):
        self._transition_state("rejected", _("Dispute rejected."))

    def action_escalate(self):
        self._transition_state("escalated", _("Dispute escalated."))

    def action_settle(self, amount=None):
        for dispute in self:
            # Validate the state transition before the amount so an
            # illegal settle (e.g. straight from 'opened') reports the
            # state-machine conflict, not a missing-amount error.
            dispute._assert_transition_allowed("settled")
            if amount is not None:
                dispute.settled_amount = amount
            if not dispute.settled_amount:
                dispute.settled_amount = dispute.offered_amount
            if not dispute.settled_amount:
                raise UserError(_(
                    "[EHL-DSP-007] Cannot mark dispute %(name)s "
                    "settled without a settled amount."
                ) % {"name": dispute.name})
        self._transition_state("settled", _("Settled."))

    def action_write_off(self):
        for dispute in self:
            dispute.settled_amount = 0.0
        self._transition_state("written_off", _("Written off."))

    def action_close(self):
        self._transition_state("closed", _("Dispute closed."))

    def action_cancel(self):
        self._transition_state("cancelled", _("Dispute cancelled."))

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_dispute_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-DSP-008] Dispute state must change via the "
                "action methods, not by direct write."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Event log helper
    # ------------------------------------------------------------------
    def _log_event(self, event_type, summary, from_state=None, to_state=None):
        self.ensure_one()
        Event = self.env["eh.log.dispute.event"].with_context(
            eh_log_dispute_internal_event_create=True,
        )
        Event.create({
            "dispute_id": self.id,
            "event_type": event_type,
            "summary": summary,
            "from_state": from_state or "",
            "to_state": to_state or "",
            "occurred_at": fields.Datetime.now(),
            "company_id": self.company_id.id,
        })

    # ------------------------------------------------------------------
    # Source-record open helper
    # ------------------------------------------------------------------
    def action_open_source_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "view_mode": "form",
            "res_id": self.res_id,
            "target": "current",
        }

    # ------------------------------------------------------------------
    # SLA breach cron
    # ------------------------------------------------------------------
    @api.model
    def cron_alert_overdue(self):
        today = fields.Date.context_today(self)
        terminal = ("settled", "closed", "cancelled", "written_off")
        candidates = self.search([
            ("sla_target_date", "<", today),
            ("state", "not in", list(terminal)),
        ])
        for dispute in candidates:
            dispute.activity_schedule(
                "mail.mail_activity_data_warning",
                summary=_("Dispute %(name)s overdue (SLA was %(date)s)") % {
                    "name": dispute.name,
                    "date": dispute.sla_target_date,
                },
                user_id=dispute.create_uid.id or self.env.uid,
            )
        return len(candidates)


class EhLogDisputeEvent(models.Model):
    _name = "eh.log.dispute.event"
    _description = "Dispute Event"
    _order = "occurred_at desc, id desc"

    dispute_id = fields.Many2one(
        "eh.log.dispute",
        string="Dispute",
        required=True,
        ondelete="cascade",
        index=True,
    )
    event_type = fields.Selection(
        [
            ("opened", "Opened"),
            ("state_change", "State Change"),
            ("correspondence", "Correspondence"),
            ("offer", "Offer"),
            ("payment", "Payment"),
            ("note", "Note"),
        ],
        string="Type",
        required=True,
        default="note",
    )
    summary = fields.Char(string="Summary", required=True)
    from_state = fields.Char(string="From State")
    to_state = fields.Char(string="To State")
    occurred_at = fields.Datetime(
        string="Occurred At",
        required=True,
        default=fields.Datetime.now,
    )
    notes = fields.Text(string="Operator Notes")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_dispute_internal_event_create"):
            raise UserError(_(
                "[EHL-DSP-009] Dispute events are created by the "
                "dispute's action methods or _log_event helper, not "
                "by direct ORM write."
            ))
        return super().create(vals_list)

    def write(self, vals):
        locked = set(EVENT_LOCKED_FIELDS) & set(vals.keys())
        if locked:
            raise UserError(_(
                "[EHL-DSP-010] Dispute event field(s) %(fields)s "
                "are immutable after creation. Append a new event "
                "instead."
            ) % {"fields": ", ".join(sorted(locked))})
        return super().write(vals)

    def unlink(self):
        if self:
            raise UserError(_(
                "[EHL-DSP-011] Dispute events are append-only and "
                "cannot be deleted."
            ))
        return super().unlink()
