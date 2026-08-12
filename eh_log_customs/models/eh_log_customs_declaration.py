# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Customs declaration: the central record of the customs broker module.

Born from a confirmed sale order alongside the freight job, advanced
through a state machine that stops at hard guards (missing HS lines,
missing regulator profile, deferment balance below the duty payable),
submits via the regulator-of-record adapter, posts a deferment debit
on assessment.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import (
    ConfigurationMissingError,
    CustomsDeclarationError,
    JobStateConflictError,
)

_logger = logging.getLogger(__name__)


DECLARATION_STATES = [
    ("draft", "Draft"),
    ("ready", "Ready"),
    ("submitted", "Submitted"),
    ("queried", "Queried by Customs"),
    ("assessed", "Assessed"),
    ("paid", "Paid"),
    ("cleared", "Cleared"),
    ("closed", "Closed"),
    ("cancelled", "Cancelled"),
    ("rejected", "Rejected"),
]

ALLOWED_DECLARATION_TRANSITIONS = {
    "draft": {"ready", "cancelled"},
    "ready": {"submitted", "draft", "cancelled"},
    "submitted": {"queried", "assessed", "rejected", "cancelled"},
    "queried": {"submitted", "rejected", "cancelled"},
    "assessed": {"paid", "rejected", "cancelled"},
    "paid": {"cleared", "rejected"},
    "cleared": {"closed"},
    "closed": set(),
    "cancelled": set(),
    "rejected": set(),
}


class EhLogCustomsDeclaration(models.Model):
    _name = "eh.log.customs.declaration"
    _description = "Customs Declaration"
    _inherit = ["mail.thread", "mail.activity.mixin", "eh.log.ux.mixin"]
    _order = "create_date desc, id desc"
    _rec_names_search = ["name", "regulator_reference"]

    # ----- Identity -----

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
        selection=DECLARATION_STATES,
        string="State",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_customs_declaration_company_rel",
        "declaration_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    # ----- Source linkage -----

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        ondelete="restrict",
        index=True,
        readonly=True,
        copy=False,
    )

    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
        ondelete="set null",
        index=True,
        copy=False,
    )

    # ----- Type and authority -----

    declaration_type_id = fields.Many2one(
        "eh.log.customs.declaration.type",
        string="Declaration Type",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        help=(
            "Import / Export / Transit / Re-export / Temporary. Determines which fields are mandatory and which regulator endpoint the adapter posts to."
        )
    )

    regulator_profile_id = fields.Many2one(
        "eh.log.adapter.profile",
        string="Regulator Profile",
        domain=[("provider_kind", "=", "regulator")],
        index=True,
        tracking=True,
        help="Adapter profile through which this declaration is "
             "submitted. Country packs ship default profiles; "
             "operators pick the right one per declaration.",
    )

    deferment_account_id = fields.Many2one(
        "eh.log.customs.deferment.account",
        string="Deferment Account",
        domain="[('regulator_profile_id', '=', regulator_profile_id), ('company_id', '=', company_id)]",
        index=True,
        tracking=True,
    )

    broker_reference = fields.Char(
        string="Broker Reference",
        index=True,
        help=(
            "Internal broker reference (your file number). Surfaces on the regulator submission and on customer invoices."
        )
    )

    regulator_reference = fields.Char(
        string="Regulator Reference",
        index=True,
        readonly=True,
        copy=False,
        help="Customs-issued declaration number returned at submission. "
             "Captured from the adapter response.",
    )

    # ----- Parties -----

    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        index=True,
        tracking=True,
    )

    importer_id = fields.Many2one(
        "res.partner",
        string="Importer or Consignee",
        index=True,
        tracking=True,
    )

    exporter_id = fields.Many2one(
        "res.partner",
        string="Exporter or Shipper",
        index=True,
        tracking=True,
    )

    # ----- Dates -----

    declaration_date = fields.Date(
        string="Declaration Date",
        default=fields.Date.context_today,
        tracking=True,
    )
    submitted_at = fields.Datetime(string="Submitted At", readonly=True, copy=False, tracking=True)
    assessed_at = fields.Datetime(string="Assessed At", readonly=True, copy=False, tracking=True)
    cleared_at = fields.Datetime(string="Cleared At", readonly=True, copy=False, tracking=True)
    closed_at = fields.Datetime(string="Closed At", readonly=True, copy=False, tracking=True)

    # ----- Lines and totals -----

    line_ids = fields.One2many(
        "eh.log.customs.declaration.line",
        "declaration_id",
        string="HS Lines",
        copy=True,
    )

    line_count = fields.Integer(
        string="Lines",
        compute="_compute_line_count",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    customs_value = fields.Monetary(
        string="Customs Value",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
        help=(
            "CIF value declared to customs. Duty and VAT are computed against this. Discrepancy between this and the supplier invoice is the #1 cause of regulator queries."
        )
    )

    duty_amount = fields.Monetary(
        string="Duty",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )

    vat_amount = fields.Monetary(
        string="VAT",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )

    payable_amount = fields.Monetary(
        string="Total Payable",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
        help="Sum of duty plus VAT plus other charges. Drawn from "
             "the deferment account on assessment.",
    )

    notes = fields.Text(string="Notes")

    # ----- Computes -----

    @api.depends("company_id")
    def _compute_company_ids(self):
        for declaration in self:
            declaration.company_ids = declaration.company_id

    @api.depends("line_ids")
    def _compute_line_count(self):
        for declaration in self:
            declaration.line_count = len(declaration.line_ids)

    @api.depends(
        "line_ids",
        "line_ids.customs_value",
        "line_ids.duty_amount",
        "line_ids.vat_amount",
    )
    def _compute_totals(self):
        for declaration in self:
            declaration.customs_value = sum(
                line.customs_value for line in declaration.line_ids
            )
            declaration.duty_amount = sum(
                line.duty_amount for line in declaration.line_ids
            )
            declaration.vat_amount = sum(
                line.vat_amount for line in declaration.line_ids
            )
            declaration.payable_amount = (
                declaration.duty_amount + declaration.vat_amount
            )

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.customs.declaration"
                ) or _("New")
        return super().create(vals_list)

    # ----- State guards -----

    def _transition_state(self, target_state: str):
        for declaration in self:
            current = declaration.state
            allowed = ALLOWED_DECLARATION_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    9,
                    _(
                        "Customs declaration %(name)s cannot move from "
                        "%(current)s to %(target)s. Allowed transitions "
                        "from %(current)s: %(allowed)s."
                    ) % {
                        "name": declaration.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            declaration.with_context(eh_log_customs_internal_state_write=True).write({
                "state": target_state,
            })
            self.env["eh.log.event"].log(
                category="state_transition",
                summary=_("Customs declaration %(name)s moved to %(state)s.") % {
                    "name": declaration.name, "state": target_state,
                },
                related_model="eh.log.customs.declaration",
                related_record_id=declaration.id,
                related_record_display=declaration.name,
                context={
                    "from_state": current,
                    "to_state": target_state,
                    "regulator": declaration.regulator_profile_id.provider_code or "",
                },
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_customs_internal_state_write"):
            raise UserError(_(
                "[EHL-CUSTOMS-DECL-001] State changes on a customs "
                "declaration must go through the action buttons. "
                "Direct writes are rejected."
            ))
        return super().write(vals)

    # ----- Pre-flight checks -----

    def _preflight_check_ready(self):
        """Validate transition draft -> ready: HS lines and customs value."""
        for declaration in self:
            blockers = []
            if not declaration.line_ids:
                blockers.append(_(
                    "Declaration has no HS lines. Add at least one HS "
                    "code with customs value before marking ready."
                ))
            for line in declaration.line_ids:
                if not line.hs_code_id:
                    blockers.append(_(
                        "Line %(seq)s has no HS code."
                    ) % {"seq": line.sequence})
                if not line.customs_value:
                    blockers.append(_(
                        "Line %(seq)s has zero customs value."
                    ) % {"seq": line.sequence})
            if not declaration.regulator_profile_id:
                blockers.append(_(
                    "Regulator profile is not set. Pick the regulator "
                    "this declaration is filed with."
                ))
            if blockers:
                raise CustomsDeclarationError(
                    10,
                    _(
                        "Declaration %(name)s cannot be marked ready. "
                        "Resolve the following before re-trying:\n\n- %(list)s"
                    ) % {
                        "name": declaration.name,
                        "list": "\n- ".join(blockers),
                    },
                )

    def _preflight_check_submit(self):
        """Validate ready -> submitted: deferment balance versus payable."""
        for declaration in self:
            type_requires_def = declaration.declaration_type_id.requires_deferment
            if type_requires_def and not declaration.deferment_account_id:
                raise CustomsDeclarationError(
                    11,
                    _(
                        "Declaration type %(type)s requires a deferment "
                        "account but none is set on declaration "
                        "%(name)s. Pick a deferment account."
                    ) % {
                        "type": declaration.declaration_type_id.display_name,
                        "name": declaration.name,
                    },
                )
            if declaration.deferment_account_id and declaration.payable_amount:
                if declaration.deferment_account_id.current_balance < declaration.payable_amount:
                    raise CustomsDeclarationError(
                        12,
                        _(
                            "Deferment account %(account)s has balance "
                            "%(balance)s, less than the declaration "
                            "payable %(payable)s. Top up before "
                            "submission."
                        ) % {
                            "account": declaration.deferment_account_id.display_name,
                            "balance": declaration.deferment_account_id.current_balance,
                            "payable": declaration.payable_amount,
                        },
                    )

    # ----- Actions -----

    def action_set_ready(self):
        self._preflight_check_ready()
        self._transition_state("ready")
        return True

    def action_submit(self):
        """Submit through the registered regulator adapter.

        When no adapter is registered (engine running standalone, no
        country pack installed), the action raises with a clear hint
        listing the registered providers. Mock-mode profiles dispatch
        through the adapter base's mock fixture path.
        """
        self._preflight_check_submit()
        from odoo.addons.eh_log_base import adapter_registry
        for declaration in self:
            profile = declaration.regulator_profile_id
            adapter_cls = adapter_registry.get(profile.provider_code)
            if not adapter_cls:
                raise ConfigurationMissingError(
                    20,
                    _(
                        "No adapter is registered for provider "
                        "'%(provider)s'. Install the country pack that "
                        "owns this regulator. Currently registered: "
                        "%(list)s."
                    ) % {
                        "provider": profile.provider_code,
                        "list": ", ".join(sorted(adapter_registry.keys())) or _("(none)"),
                    },
                )
            adapter = adapter_cls(profile)
            payload = declaration._build_submit_payload()
            result = adapter.call(
                message_type="declaration_submit",
                payload=payload,
                related_model="eh.log.customs.declaration",
                related_record_id=declaration.id,
                related_record_display=declaration.name,
                idempotency_key=f"submit-{declaration.id}-{declaration.broker_reference or ''}",
            )
            if result.status == "success":
                # Adapters that parse a regulator reference into the
                # response will surface it; default empty here.
                ref = (
                    result.parsed.get("regulator_reference")
                    if isinstance(result.parsed, dict) else None
                )
                if ref:
                    declaration.with_context(eh_log_customs_internal_state_write=False).write({
                        "regulator_reference": ref,
                    })
                declaration.submitted_at = fields.Datetime.now()
                declaration._transition_state("submitted")
            elif result.status == "rejected":
                declaration._transition_state("rejected")
                declaration.message_post(body=_(
                    "Regulator rejected submission. Code %(code)s: "
                    "%(message)s"
                ) % {
                    "code": result.error_code or "?",
                    "message": result.error_message or "?",
                })
            else:
                declaration.message_post(body=_(
                    "Submission failed (status %(status)s). The "
                    "declaration stays in 'ready'. Re-submit from the "
                    "form or replay from the message log."
                ) % {"status": result.status})
        return True

    def action_set_assessed(self):
        self._transition_state("assessed")
        for declaration in self:
            declaration.assessed_at = fields.Datetime.now()
        return True

    def action_pay(self):
        """Mark assessed declaration as paid; debit the deferment account."""
        for declaration in self:
            if declaration.deferment_account_id and declaration.payable_amount:
                self.env["eh.log.customs.deferment.entry"].create({
                    "account_id": declaration.deferment_account_id.id,
                    "entry_kind": "debit",
                    "amount": declaration.payable_amount,
                    "description": _(
                        "Duty and VAT for declaration %(name)s"
                    ) % {"name": declaration.name},
                    "declaration_id": declaration.id,
                    "state": "posted",
                    "posted_at": fields.Datetime.now(),
                })
            declaration._transition_state("paid")
        return True

    def action_set_cleared(self):
        self._transition_state("cleared")
        for declaration in self:
            declaration.cleared_at = fields.Datetime.now()
        return True

    def action_close(self):
        self._transition_state("closed")
        for declaration in self:
            declaration.closed_at = fields.Datetime.now()
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True

    def action_set_queried(self):
        self._transition_state("queried")
        return True

    # ----- Internals -----

    def _build_submit_payload(self) -> dict:
        """Compose the adapter payload from declaration state.

        Concrete adapters serialise this dict into their wire format
        (XML for Mirsal, JSON for FASAH, etc.). The dict shape is
        deliberately neutral so any country pack can map it.
        """
        self.ensure_one()
        return {
            "broker_reference": self.broker_reference,
            "declaration_type": self.declaration_type_id.code,
            "declaration_date": (
                self.declaration_date.isoformat() if self.declaration_date else None
            ),
            "currency": self.currency_id.name,
            "customs_value": self.customs_value,
            "duty_amount": self.duty_amount,
            "vat_amount": self.vat_amount,
            "payable_amount": self.payable_amount,
            "importer": {
                "name": self.importer_id.display_name if self.importer_id else None,
                "vat": self.importer_id.vat if self.importer_id else None,
            },
            "exporter": {
                "name": self.exporter_id.display_name if self.exporter_id else None,
                "vat": self.exporter_id.vat if self.exporter_id else None,
            },
            "lines": [
                {
                    "hs_code": line.hs_code_id.code if line.hs_code_id else None,
                    "description": line.description,
                    "country_of_origin": (
                        line.country_of_origin_id.code if line.country_of_origin_id else None
                    ),
                    "quantity": line.quantity,
                    "unit_value": line.unit_value,
                    "customs_value": line.customs_value,
                    "duty_rate_pct": line.duty_rate_pct,
                    "vat_rate_pct": line.vat_rate_pct,
                    "duty_amount": line.duty_amount,
                    "vat_amount": line.vat_amount,
                }
                for line in self.line_ids
            ],
        }
