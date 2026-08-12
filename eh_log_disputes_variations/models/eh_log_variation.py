# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Variation (change order) spine + lines.

A variation modifies a confirmed sale order: adds charges, removes
charges, changes prices. Distinct from a new quote because it
inherits the customer relationship, the credit posture, the KYC
posture, and the operational links.

State machine:

    draft -> submitted -> approved -> applied -> closed
                       \-> rejected -> draft
                                    \-> cancelled

The ``apply`` step pushes the variation lines onto the source sale
order as new lines. Once applied, the variation is locked; further
changes require a new variation.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .eh_log_dispute import ALLOWED_SOURCE_MODELS

_logger = logging.getLogger(__name__)


# Reuse the dispute allow-list; both domains target the same
# operational-record set. A variation against a transport trip might
# add an additional stop charge, against a freight job a re-routing
# fee, against a sale order a new line item.
VARIATION_ALLOWED_SOURCE_MODELS = set(ALLOWED_SOURCE_MODELS)


ALLOWED_TRANSITIONS = {
    "draft":     ("submitted", "cancelled"),
    "submitted": ("approved", "rejected", "cancelled"),
    "approved":  ("applied", "rejected", "cancelled"),
    "applied":   ("closed",),
    "rejected":  ("draft", "cancelled"),
    "closed":    (),
    "cancelled": (),
}


class EhLogVariation(models.Model):
    _name = "eh.log.variation"
    _description = "Variation"
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
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("applied", "Applied"),
            ("rejected", "Rejected"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
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
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Linked Sale Order",
        compute="_compute_sale_order",
        store=True,
        help=(
            "Sale order the apply step writes to. Resolved from the "
            "polymorphic source: a sale-order source is itself; a "
            "freight-job or other source resolves to its parent "
            "sale order if linked."
        ),
    )
    line_ids = fields.One2many(
        "eh.log.variation.line",
        "variation_id",
        string="Lines",
    )
    line_count = fields.Integer(
        string="Lines",
        compute="_compute_line_count",
    )
    net_amount = fields.Monetary(
        string="Net Variation",
        compute="_compute_net_amount",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    submitted_at = fields.Datetime(string="Submitted At", readonly=True)
    approved_at = fields.Datetime(string="Approved At", readonly=True)
    approved_by_id = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
    )
    applied_at = fields.Datetime(string="Applied At", readonly=True)
    applied_line_ids = fields.Many2many(
        "sale.order.line",
        "eh_log_variation_applied_line_rel",
        "variation_id",
        "order_line_id",
        string="Applied Sale Order Lines",
        readonly=True,
        copy=False,
        help=(
            "Sale-order lines actually created by the apply step. "
            "Stored so a future cancellation knows which lines to "
            "reverse."
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
                    "eh.log.variation"
                ) or _("New")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("res_model", "res_id")
    def _compute_source_display(self):
        for variation in self:
            if not variation.res_model or not variation.res_id:
                variation.source_display = ""
                continue
            Model = self.env.get(variation.res_model)
            if Model is None:
                variation.source_display = (
                    f"{variation.res_model}/{variation.res_id}"
                )
                continue
            record = Model.browse(variation.res_id).exists()
            variation.source_display = (
                record.display_name if record
                else f"{variation.res_model}/{variation.res_id}"
            )

    @api.depends("res_model", "res_id")
    def _compute_sale_order(self):
        for variation in self:
            if variation.res_model == "sale.order":
                variation.sale_order_id = variation.res_id
                continue
            Model = self.env.get(variation.res_model)
            if Model is None:
                variation.sale_order_id = False
                continue
            record = Model.browse(variation.res_id).exists()
            if record and "sale_order_id" in record._fields:
                variation.sale_order_id = record.sale_order_id
            else:
                variation.sale_order_id = False

    @api.depends("line_ids")
    def _compute_line_count(self):
        for variation in self:
            variation.line_count = len(variation.line_ids)

    @api.depends("line_ids.amount_subtotal")
    def _compute_net_amount(self):
        for variation in self:
            variation.net_amount = sum(
                variation.line_ids.mapped("amount_subtotal")
            )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("res_model")
    def _check_res_model_allowed(self):
        for variation in self:
            if variation.res_model not in VARIATION_ALLOWED_SOURCE_MODELS:
                raise ValidationError(_(
                    "[EHL-VAR-001] Source model %(model)s is not in "
                    "the variation allow-list."
                ) % {"model": variation.res_model})

    @api.constrains("res_model", "res_id")
    def _check_source_record_exists(self):
        for variation in self:
            Model = self.env.get(variation.res_model)
            if Model is None:
                continue
            if not Model.browse(variation.res_id).exists():
                raise ValidationError(_(
                    "[EHL-VAR-002] Source record %(model)s/%(id)s "
                    "does not exist."
                ) % {"model": variation.res_model, "id": variation.res_id})

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for variation in self:
            current = variation.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Variation %(name)s cannot move from "
                      "%(from)s to %(to)s.") % {
                        "name": variation.name,
                        "from": current,
                        "to": target_state,
                    },
                )
            variation.with_context(
                eh_log_variation_internal_state_write=True
            ).write({"state": target_state})

    def action_submit(self):
        for variation in self:
            if not variation.line_ids:
                raise UserError(_(
                    "[EHL-VAR-003] Variation %(name)s has no lines; "
                    "add at least one before submitting."
                ) % {"name": variation.name})
        self._transition_state("submitted")
        for variation in self:
            variation.submitted_at = fields.Datetime.now()

    def action_approve(self):
        self._transition_state("approved")
        for variation in self:
            variation.approved_at = fields.Datetime.now()
            variation.approved_by_id = self.env.user.id

    def action_reject(self):
        self._transition_state("rejected")

    def action_reset_to_draft(self):
        self._transition_state("draft")

    def action_cancel(self):
        self._transition_state("cancelled")

    def action_apply(self):
        for variation in self:
            if not variation.sale_order_id:
                raise UserError(_(
                    "[EHL-VAR-004] Variation %(name)s has no "
                    "linked sale order; cannot apply."
                ) % {"name": variation.name})
            new_lines = self.env["sale.order.line"]
            for line in variation.line_ids:
                # Add as new SO line; the variation reference is
                # stored so a future reversal can find these.
                new_line = self.env["sale.order.line"].with_context(eh_log_force_charge_product=True).create({
                    "order_id": variation.sale_order_id.id,
                    "name": _(
                        "[%(ref)s] %(desc)s"
                    ) % {
                        "ref": variation.name,
                        "desc": line.description,
                    },
                    "product_uom_qty": line.quantity,
                    "price_unit": line.unit_price,
                })
                new_lines |= new_line
            variation.applied_line_ids = [(6, 0, new_lines.ids)]
        self._transition_state("applied")
        for variation in self:
            variation.applied_at = fields.Datetime.now()

    def action_close(self):
        self._transition_state("closed")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_variation_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-VAR-005] Variation state must change via the "
                "action methods."
            ))
        return super().write(vals)


class EhLogVariationLine(models.Model):
    _name = "eh.log.variation.line"
    _description = "Variation Line"
    _order = "variation_id, sequence, id"

    variation_id = fields.Many2one(
        "eh.log.variation",
        string="Variation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Char(string="Description", required=True)
    quantity = fields.Float(string="Quantity", required=True, default=1.0)
    unit_price = fields.Monetary(
        string="Unit Price",
        required=True,
        currency_field="currency_id",
        help=(
            "Price per unit. Negative values are permitted (and "
            "expected) for a charge reduction."
        ),
    )
    amount_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amount_subtotal",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="variation_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="variation_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("quantity", "unit_price")
    def _compute_amount_subtotal(self):
        for line in self:
            line.amount_subtotal = line.quantity * line.unit_price

    def write(self, vals):
        for line in self:
            if line.variation_id.state in ("approved", "applied", "closed", "cancelled"):
                raise UserError(_(
                    "[EHL-VAR-006] Variation %(name)s is %(state)s; "
                    "lines are read-only."
                ) % {
                    "name": line.variation_id.name,
                    "state": line.variation_id.state,
                })
        return super().write(vals)
