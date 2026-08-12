# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Last-mile delivery: one stop on a wave.

State machine: scheduled -> out_for_delivery -> delivered / failed /
returned. Failure routes to return after the configurable maximum
attempts threshold.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


DELIVERY_STATES = [
    ("scheduled", "Scheduled"),
    ("out_for_delivery", "Out for Delivery"),
    ("delivered", "Delivered"),
    ("failed", "Failed"),
    ("returned", "Returned"),
    ("cancelled", "Cancelled"),
]

ALLOWED_DELIVERY_TRANSITIONS = {
    "scheduled": {"out_for_delivery", "cancelled"},
    "out_for_delivery": {"delivered", "failed", "cancelled"},
    "delivered": set(),
    "failed": {"returned", "scheduled"},
    "returned": set(),
    "cancelled": set(),
}


class EhLogLastMileDelivery(models.Model):
    _name = "eh.log.last.mile.delivery"
    _description = "Last Mile Delivery"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _order = "wave_id, sequence, scheduled_window_start"
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
        selection=DELIVERY_STATES,
        string="State",
        default="scheduled",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    wave_id = fields.Many2one(
        "eh.log.last.mile.wave",
        string="Wave",
        ondelete="set null",
        index=True,
        tracking=True,
        help=(
            "Delivery wave this drop belongs to. The wave groups deliveries by driver / vehicle / planned date so dispatch is one click."
        )
    )

    sequence = fields.Integer(
        default=10,
        help="Stop order within the wave. The driver visits stops in "
             "sequence; the dispatcher reorders by drag-and-drop.",
    )

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="restrict",
        index=True,
    )

    # ----- Customer -----

    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        index=True,
        tracking=True,
    )

    customer_reference = fields.Char(
        string="Customer Reference",
        tracking=True,
    )

    delivery_partner_id = fields.Many2one(
        "res.partner",
        string="Delivery Address",
        index=True,
        help="Defaults to the customer's address; override for a "
             "ship-to-third-party scenario.",
    )

    # ----- Schedule -----

    scheduled_window_start = fields.Datetime(
        string="Window Start",
        required=True,
        index=True,
        help=(
            "Start of the customer's promised delivery window. Out-of-window delivery counts against the SLA on the customer dashboard."
        )
    )

    scheduled_window_end = fields.Datetime(
        string="Window End",
        required=True,
        index=True,
        help=(
            "End of the customer's promised delivery window."
        )
    )

    delivered_at = fields.Datetime(
        string="Delivered At",
        readonly=True,
        copy=False,
        tracking=True,
    )

    # ----- Cargo -----

    package_count = fields.Integer(
        string="Packages",
        default=1,
        help=(
            "Number of physical pieces. Affects load planning and is reconciled with the warehouse pick on dispatch."
        )
    )

    cargo_description = fields.Char(string="Cargo Description")

    weight_kg = fields.Float(string="Weight (kg)")

    # ----- COD -----

    cod_amount = fields.Monetary(
        string="COD Expected",
        currency_field="currency_id",
        help="Cash to collect on delivery. Zero for non-COD stops.",
    )

    cod_collected_amount = fields.Monetary(
        string="COD Collected",
        currency_field="currency_id",
        readonly=True,
        copy=False,
        help="Captured at delivery confirmation. Driven by the "
             "Delivered action; cannot exceed cod_amount.",
    )

    cod_collection_method = fields.Selection(
        selection=[
            ("cash", "Cash"),
            ("card", "Card"),
            ("transfer", "Bank Transfer"),
            ("none", "Not Applicable"),
        ],
        string="Collection Method",
        default="none",
        readonly=True,
        copy=False,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    # ----- ePOD -----

    recipient_name = fields.Char(string="Recipient Name", readonly=True, copy=False)
    recipient_role = fields.Char(string="Recipient Role", readonly=True, copy=False)

    signature_image = fields.Binary(
        string="Signature",
        attachment=True,
        readonly=True,
        copy=False,
    )

    photo_image = fields.Binary(
        string="Photo",
        attachment=True,
        readonly=True,
        copy=False,
    )

    # ----- Attempts -----

    attempt_ids = fields.One2many(
        "eh.log.last.mile.attempt",
        "delivery_id",
        string="Attempts",
    )

    attempt_count = fields.Integer(
        string="Attempts",
        compute="_compute_attempt_count",
        store=True,
    )

    # ----- Returns -----

    return_to_sender = fields.Boolean(
        string="Return to Sender",
        default=False,
        help="Set when a returned delivery should go back to the "
             "shipper rather than be re-attempted.",
    )

    return_reason = fields.Selection(
        selection=[
            ("max_attempts", "Maximum Attempts Reached"),
            ("address_incorrect", "Address Incorrect"),
            ("refused", "Refused"),
            ("damaged", "Damaged"),
            ("recall", "Customer Recall"),
            ("other", "Other"),
        ],
        string="Return Reason",
        copy=False,
    )

    notes = fields.Text(string="Notes")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ----- Computes -----

    @api.depends("attempt_ids")
    def _compute_attempt_count(self):
        for delivery in self:
            delivery.attempt_count = len(delivery.attempt_ids)

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.last.mile.delivery"
                ) or _("New")
            if not vals.get("delivery_partner_id") and vals.get("customer_id"):
                vals["delivery_partner_id"] = vals["customer_id"]
        return super().create(vals_list)

    def _transition_state(self, target_state: str):
        for delivery in self:
            current = delivery.state
            allowed = ALLOWED_DELIVERY_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    160,
                    _(
                        "Delivery %(name)s cannot move from %(current)s "
                        "to %(target)s. Allowed transitions from "
                        "%(current)s: %(allowed)s."
                    ) % {
                        "name": delivery.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            delivery.with_context(eh_log_last_mile_delivery_state_write=True).write({
                "state": target_state,
            })

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_last_mile_delivery_state_write"):
            raise UserError(_(
                "[EHL-LM-DEL-001] State changes on a delivery must go "
                "through the action buttons. Direct writes are rejected."
            ))
        return super().write(vals)

    # ----- Actions -----

    def action_set_out_for_delivery(self):
        self._transition_state("out_for_delivery")
        return True

    def action_mark_delivered(self, recipient_name=None, recipient_role=None,
                              signature_image=None, photo_image=None,
                              cod_collected=None, cod_method=None):
        for delivery in self:
            if delivery.cod_amount and not cod_collected:
                raise UserError(_(
                    "[EHL-LM-DEL-002] Delivery %(name)s expects a COD "
                    "collection of %(amount)s. Capture the collected "
                    "amount before marking delivered."
                ) % {"name": delivery.name, "amount": delivery.cod_amount})
            if cod_collected and cod_collected > delivery.cod_amount:
                raise UserError(_(
                    "[EHL-LM-DEL-003] COD collected %(collected)s "
                    "exceeds expected %(expected)s on delivery "
                    "%(name)s."
                ) % {
                    "collected": cod_collected,
                    "expected": delivery.cod_amount,
                    "name": delivery.name,
                })
            delivery._transition_state("delivered")
            vals = {
                "delivered_at": fields.Datetime.now(),
            }
            if recipient_name:
                vals["recipient_name"] = recipient_name
            if recipient_role:
                vals["recipient_role"] = recipient_role
            if signature_image:
                vals["signature_image"] = signature_image
            if photo_image:
                vals["photo_image"] = photo_image
            if cod_collected:
                vals["cod_collected_amount"] = cod_collected
            if cod_method:
                vals["cod_collection_method"] = cod_method
            delivery.with_context(eh_log_last_mile_delivery_state_write=True).write(vals)
            # Auto-create a successful attempt entry.
            self.env["eh.log.last.mile.attempt"].sudo().create({
                "delivery_id": delivery.id,
                "outcome": "delivered",
                "happened_at": fields.Datetime.now(),
                "notes": _("Delivered to %s") % (recipient_name or "recipient"),
            })
        return True

    def action_mark_failed(self, outcome="customer_not_home", notes=None):
        """Record a failed attempt; route to failed if max attempts reached."""
        max_attempts = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "eh_log_last_mile.max_attempts", default="3",
            )
        )
        Attempt = self.env["eh.log.last.mile.attempt"].sudo()
        for delivery in self:
            Attempt.create({
                "delivery_id": delivery.id,
                "outcome": outcome,
                "happened_at": fields.Datetime.now(),
                "notes": notes,
            })
            delivery.invalidate_recordset()
            if delivery.attempt_count >= max_attempts:
                delivery._transition_state("failed")
            else:
                # Stay out_for_delivery; another attempt may follow.
                pass
        return True

    def action_return_to_sender(self):
        for delivery in self:
            delivery._transition_state("returned")
            delivery.return_to_sender = True
            if not delivery.return_reason:
                delivery.return_reason = "max_attempts"
        return True

    def action_reschedule(self):
        """Move a failed delivery back to scheduled for a fresh attempt."""
        for delivery in self:
            delivery._transition_state("scheduled")
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True
