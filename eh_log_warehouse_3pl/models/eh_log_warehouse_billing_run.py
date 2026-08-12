# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Periodic billing run.

Computes one billing batch per (client, period). Reads the movement
log for handling charges and the snapshot history for storage charges,
both through the client's rate card. Emits a draft sale order so the
operator can review and confirm before the customer is invoiced.

State machine: draft -> computed -> posted -> cancelled. The compute
step is destructive of prior lines (so re-running picks up new
movements); posting is what writes to the sale order. Once posted,
the run is locked.
"""
import logging
from calendar import monthrange
from datetime import date, datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .eh_log_warehouse_rate_card import SERVICE_TYPES

_logger = logging.getLogger(__name__)


ALLOWED_TRANSITIONS = {
    "draft": ("computed", "cancelled"),
    "computed": ("posted", "draft", "cancelled"),
    "posted": (),
    "cancelled": (),
}


class EhLogWarehouseBillingRun(models.Model):
    _name = "eh.log.warehouse.billing.run"
    _description = "Warehouse Billing Run"
    _order = "period_end desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]

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
            ("computed", "Computed"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    client_id = fields.Many2one(
        "eh.log.warehouse.client",
        string="3PL Client",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    rate_card_id = fields.Many2one(
        "eh.log.warehouse.rate.card",
        string="Rate Card",
        required=True,
        tracking=True,
        help=(
            "Rate card snapshotted onto the run. Defaults to the "
            "client's current card; can be overridden for replays."
        ),
    )
    period_start = fields.Date(
        string="Period Start",
        required=True,
        tracking=True,
    )
    period_end = fields.Date(
        string="Period End",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        "eh.log.warehouse.billing.line",
        "run_id",
        string="Lines",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Generated Sale Order",
        readonly=True,
        copy=False,
    )
    total = fields.Monetary(
        string="Total",
        compute="_compute_total",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="rate_card_id.currency_id",
        store=True,
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
                    "eh.log.warehouse.billing.run"
                ) or _("New")
            if "rate_card_id" not in vals and vals.get("client_id"):
                client = self.env["eh.log.warehouse.client"].browse(vals["client_id"])
                vals["rate_card_id"] = client.rate_card_id.id
        return super().create(vals_list)

    @api.depends("line_ids.subtotal")
    def _compute_total(self):
        for run in self:
            run.total = sum(run.line_ids.mapped("subtotal"))

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for run in self:
            if run.period_start > run.period_end:
                raise UserError(_(
                    "[EHL-WHS-020] Billing run period start "
                    "%(start)s is after period end %(end)s."
                ) % {"start": run.period_start, "end": run.period_end})

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def _transition_state(self, target_state):
        for run in self:
            current = run.state
            allowed = ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise JobStateConflictError(
                    1,
                    _("Billing run %(name)s cannot move from "
                      "%(from)s to %(to)s.") % {
                        "name": run.name, "from": current, "to": target_state,
                    },
                )
            run.with_context(
                eh_log_warehouse_internal_state_write=True
            ).write({"state": target_state})

    def action_compute(self):
        for run in self:
            run.line_ids.with_context(
                eh_log_warehouse_internal_billing=True
            ).unlink()
            run._compute_charges()
        self._transition_state("computed")

    def action_post(self):
        for run in self:
            if not run.line_ids:
                raise UserError(_(
                    "[EHL-WHS-021] Billing run %(name)s has no "
                    "computed lines."
                ) % {"name": run.name})
            order = run._create_sale_order()
            run.sale_order_id = order.id
        self._transition_state("posted")

    def action_reset_to_draft(self):
        self._transition_state("draft")

    def action_cancel(self):
        self._transition_state("cancelled")

    def write(self, vals):
        if "state" in vals and not self.env.context.get(
            "eh_log_warehouse_internal_state_write"
        ):
            raise UserError(_(
                "[EHL-WHS-022] Billing run state must change via "
                "the action buttons."
            ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Compute engine
    # ------------------------------------------------------------------
    def _compute_charges(self):
        self.ensure_one()
        Movement = self.env["eh.log.warehouse.movement"]
        Snapshot = self.env["eh.log.warehouse.snapshot"]
        BillingLine = self.env["eh.log.warehouse.billing.line"].with_context(
            eh_log_warehouse_internal_billing=True,
        )
        period_start_dt = datetime.combine(self.period_start, time.min)
        period_end_dt = datetime.combine(self.period_end, time.max)

        # Handling charges: count pallets per movement type in the period.
        movement_groups = Movement._read_group(
            domain=[
                ("client_id", "=", self.client_id.id),
                ("occurred_at", ">=", period_start_dt),
                ("occurred_at", "<=", period_end_dt),
            ],
            groupby=["movement_type"],
            aggregates=["pallet_count:sum"],
        )
        type_to_service = {
            "receipt": "handling_in",
            "pick": "handling_out",
        }
        for movement_type, pallet_count in movement_groups:
            service_code = type_to_service.get(movement_type)
            if not service_code:
                continue
            quantity = pallet_count or 0
            rate = self.rate_card_id.find_rate(service_code)
            if not rate:
                _logger.info(
                    "Billing run %s: no rate for %s; skipped.",
                    self.name, service_code,
                )
                continue
            BillingLine.create({
                "run_id": self.id,
                "service_type": service_code,
                "quantity": max(quantity, rate.minimum_quantity),
                "unit_price": rate.unit_price,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
            })

        # Storage charge: sum / average / peak of daily snapshots.
        snapshots = Snapshot.search([
            ("client_id", "=", self.client_id.id),
            ("snapshot_date", ">=", self.period_start),
            ("snapshot_date", "<=", self.period_end),
        ])
        if snapshots:
            day_totals = {}
            for snap in snapshots:
                day_totals.setdefault(snap.snapshot_date, 0)
                day_totals[snap.snapshot_date] += snap.pallets_on_hand
            basis = self.client_id.storage_charging_basis
            if basis == "snapshot_average":
                pallet_days = sum(day_totals.values())
                billable = pallet_days
            elif basis == "snapshot_peak":
                peak = max(day_totals.values())
                day_count = (self.period_end - self.period_start).days + 1
                billable = peak * day_count
            else:  # snapshot_first_of_month
                first = sorted(day_totals.keys())[0]
                day_count = (self.period_end - self.period_start).days + 1
                billable = day_totals[first] * day_count
            storage_rate = self.rate_card_id.find_rate("storage_pallet_day")
            if storage_rate:
                BillingLine.create({
                    "run_id": self.id,
                    "service_type": "storage_pallet_day",
                    "quantity": max(billable, storage_rate.minimum_quantity),
                    "unit_price": storage_rate.unit_price,
                    "currency_id": self.currency_id.id,
                    "company_id": self.company_id.id,
                })

        # Monthly minimum top-up.
        minimum_rate = self.rate_card_id.find_rate("monthly_minimum")
        if minimum_rate:
            existing_total = sum(self.line_ids.mapped("subtotal"))
            shortfall = minimum_rate.unit_price - existing_total
            if shortfall > 0:
                BillingLine.create({
                    "run_id": self.id,
                    "service_type": "monthly_minimum",
                    "quantity": 1.0,
                    "unit_price": shortfall,
                    "currency_id": self.currency_id.id,
                    "company_id": self.company_id.id,
                })

    def _create_sale_order(self):
        self.ensure_one()
        SaleOrder = self.env["sale.order"]
        order_vals = {
            "partner_id": self.client_id.partner_id.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "client_order_ref": self.name,
            "eh_log_warehouse_billing_run_id": self.id,
        }
        order = SaleOrder.create(order_vals)
        product = self.env.ref(
            "eh_log_warehouse_3pl.product_warehouse_billing",
            raise_if_not_found=False,
        )
        for line in self.line_ids:
            self.env["sale.order.line"].with_context(eh_log_force_charge_product=True).create({
                "order_id": order.id,
                "name": _(
                    "%(service)s (%(period_start)s to %(period_end)s)"
                ) % {
                    "service": dict(SERVICE_TYPES).get(
                        line.service_type, line.service_type,
                    ),
                    "period_start": self.period_start,
                    "period_end": self.period_end,
                },
                "product_id": product.id if product else False,
                "product_uom_qty": line.quantity,
                "price_unit": line.unit_price,
            })
        return order

    @api.model
    def cron_run_monthly_billing(self):
        """Sweep clients whose billing day matches today.

        Creates a draft run for the prior calendar month per client.
        Idempotent: skips clients whose prior-month run already
        exists in any non-cancelled state.
        """
        today = date.today()
        # Period is the prior calendar month: 1st to last day.
        prior_month_end_year = today.year if today.month > 1 else today.year - 1
        prior_month = today.month - 1 if today.month > 1 else 12
        period_start = date(prior_month_end_year, prior_month, 1)
        last_day = monthrange(prior_month_end_year, prior_month)[1]
        period_end = date(prior_month_end_year, prior_month, last_day)
        Client = self.env["eh.log.warehouse.client"].search([
            ("billing_day", "=", today.day),
            ("active", "=", True),
        ])
        created = 0
        for client in Client:
            existing = self.search([
                ("client_id", "=", client.id),
                ("period_start", "=", period_start),
                ("period_end", "=", period_end),
                ("state", "!=", "cancelled"),
            ])
            if existing:
                continue
            self.create({
                "client_id": client.id,
                "rate_card_id": client.rate_card_id.id,
                "period_start": period_start,
                "period_end": period_end,
                "company_id": client.company_id.id,
            })
            created += 1
        _logger.info(
            "Monthly warehouse billing cron: created %d run(s)", created,
        )
        return created


class EhLogWarehouseBillingLine(models.Model):
    _name = "eh.log.warehouse.billing.line"
    _description = "Warehouse Billing Line"
    _order = "run_id, service_type"

    run_id = fields.Many2one(
        "eh.log.warehouse.billing.run",
        string="Billing Run",
        required=True,
        ondelete="cascade",
        index=True,
    )
    service_type = fields.Selection(
        SERVICE_TYPES,
        string="Service",
        required=True,
    )
    quantity = fields.Float(string="Quantity", required=True)
    unit_price = fields.Monetary(
        string="Unit Price",
        required=True,
        currency_field="currency_id",
    )
    subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_subtotal",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
    )

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("eh_log_warehouse_internal_billing"):
            raise UserError(_(
                "[EHL-WHS-023] Billing lines are created by the "
                "compute action; direct ORM creates are blocked."
            ))
        return super().create(vals_list)

    def unlink(self):
        if self and not self.env.context.get("eh_log_warehouse_internal_billing"):
            raise UserError(_(
                "[EHL-WHS-024] Billing lines can only be cleared "
                "by re-running the compute action."
            ))
        return super().unlink()
