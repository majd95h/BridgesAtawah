# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dangerous goods declaration.

Per shipment. Mode (sea / air / road / rail) drives which signatory
text and footer note appears on the printed Shipper's Declaration.
The segregation detector scans the declaration's lines and flags
incompatible class combinations.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import (
    EhLogValidationError,
    JobStateConflictError,
)

_logger = logging.getLogger(__name__)


DG_STATES = [
    ("draft", "Draft"),
    ("ready", "Ready"),
    ("issued", "Issued"),
    ("cancelled", "Cancelled"),
]

ALLOWED_DG_TRANSITIONS = {
    "draft": {"ready", "cancelled"},
    "ready": {"issued", "draft", "cancelled"},
    "issued": set(),
    "cancelled": set(),
}

DG_MODES = [
    ("sea", "Sea (IMDG)"),
    ("air", "Air (IATA DGR)"),
    ("road", "Road (ADR)"),
    ("rail", "Rail (RID)"),
    ("multimodal", "Multimodal"),
]


class EhLogDgDeclaration(models.Model):
    _name = "eh.log.dg.declaration"
    _description = "Dangerous Goods Declaration"
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
        selection=DG_STATES,
        string="State",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    mode = fields.Selection(
        selection=DG_MODES,
        string="Mode",
        required=True,
        index=True,
        tracking=True,
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
        "eh_log_dg_declaration_company_rel",
        "declaration_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    # ----- Linkage -----

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

    # ----- Parties -----

    shipper_id = fields.Many2one("res.partner", string="Shipper", required=True, index=True, tracking=True)
    consignee_id = fields.Many2one("res.partner", string="Consignee", required=True, index=True, tracking=True)
    notify_party_id = fields.Many2one("res.partner", string="Notify Party")

    emergency_contact_name = fields.Char(string="Emergency Contact (24h)", required=True, tracking=True)
    emergency_contact_phone = fields.Char(string="Emergency Phone (24h)", required=True, tracking=True)

    # ----- Lane -----

    pol_name = fields.Char(string="Port or Airport of Loading")
    pod_name = fields.Char(string="Port or Airport of Discharge")
    vessel_name = fields.Char(string="Vessel", help="Sea only.")
    voyage_number = fields.Char(string="Voyage", help="Sea only.")
    flight_number = fields.Char(string="Flight", help="Air only.")

    # ----- Lines -----

    line_ids = fields.One2many(
        "eh.log.dg.declaration.line",
        "declaration_id",
        string="UN Lines",
        copy=True,
    )

    line_count = fields.Integer(
        string="Lines",
        compute="_compute_line_count",
    )

    # ----- Segregation -----

    segregation_status = fields.Selection(
        selection=[
            ("ok", "Compatible"),
            ("warning", "Incompatibilities Detected"),
            ("not_assessed", "Not Assessed"),
        ],
        string="Segregation",
        compute="_compute_segregation",
        store=True,
        help="Computed from the lines' primary classes versus each "
             "class's incompatibility list.",
    )

    segregation_summary = fields.Text(
        string="Segregation Summary",
        compute="_compute_segregation",
        store=True,
    )

    # ----- Signatory -----

    issued_by_id = fields.Many2one(
        "res.users",
        string="Issued By",
        readonly=True,
        copy=False,
    )

    issued_at = fields.Datetime(
        string="Issued At",
        readonly=True,
        copy=False,
    )

    # ----- Marine pollutant aggregate -----

    has_marine_pollutant = fields.Boolean(
        string="Marine Pollutant on Board",
        compute="_compute_marine_pollutant",
        store=True,
    )

    notes = fields.Text(string="Notes")

    # ----- Computes -----

    @api.depends("company_id")
    def _compute_company_ids(self):
        for record in self:
            record.company_ids = record.company_id

    @api.depends("line_ids")
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    @api.depends(
        "line_ids",
        "line_ids.un_number_id",
        "line_ids.un_number_id.primary_class_id",
        "line_ids.un_number_id.primary_class_id.incompatible_class_ids",
    )
    def _compute_segregation(self):
        for declaration in self:
            if not declaration.line_ids:
                declaration.segregation_status = "not_assessed"
                declaration.segregation_summary = False
                continue
            classes = declaration.line_ids.mapped(
                "un_number_id.primary_class_id"
            )
            class_set = set(classes.ids)
            incompatibilities = []
            seen_pairs = set()
            for cls in classes:
                for incompatible in cls.incompatible_class_ids:
                    if incompatible.id in class_set and incompatible.id != cls.id:
                        pair = tuple(sorted([cls.id, incompatible.id]))
                        if pair in seen_pairs:
                            continue
                        seen_pairs.add(pair)
                        incompatibilities.append(
                            f"Class {cls.code} cannot ship with class {incompatible.code} "
                            f"on the same transport unit without segregation."
                        )
            if incompatibilities:
                declaration.segregation_status = "warning"
                declaration.segregation_summary = "\n".join(incompatibilities)
            else:
                declaration.segregation_status = "ok"
                declaration.segregation_summary = (
                    "No class-level incompatibilities detected across "
                    f"{len(class_set)} class(es) on this declaration."
                )

    @api.depends("line_ids", "line_ids.un_number_id.marine_pollutant")
    def _compute_marine_pollutant(self):
        for declaration in self:
            declaration.has_marine_pollutant = any(
                line.un_number_id.marine_pollutant for line in declaration.line_ids
            )

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.dg.declaration"
                ) or _("New")
        return super().create(vals_list)

    # ----- Mode-specific validation -----

    @api.constrains("mode", "line_ids")
    def _check_mode_specific_rules(self):
        for declaration in self:
            if declaration.mode != "air":
                continue
            for line in declaration.line_ids:
                un = line.un_number_id
                if not un:
                    continue
                if un.iata_passenger_aircraft_forbidden and un.iata_cargo_aircraft_forbidden:
                    raise EhLogValidationError(
                        131,
                        _(
                            "UN %(un)s (%(name)s) is forbidden on both "
                            "passenger and cargo aircraft per IATA DGR. "
                            "It cannot appear on an air declaration."
                        ) % {
                            "un": un.un_number,
                            "name": un.proper_shipping_name,
                        },
                    )

    # ----- State transitions -----

    def _transition_state(self, target_state: str):
        for declaration in self:
            current = declaration.state
            allowed = ALLOWED_DG_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    132,
                    _(
                        "DG declaration %(name)s cannot move from "
                        "%(current)s to %(target)s. Allowed transitions "
                        "from %(current)s: %(allowed)s."
                    ) % {
                        "name": declaration.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            declaration.with_context(eh_log_dg_internal_state_write=True).write({
                "state": target_state,
            })
            self.env["eh.log.event"].log(
                category="state_transition",
                summary=_("DG declaration %(name)s moved to %(state)s.") % {
                    "name": declaration.name, "state": target_state,
                },
                related_model="eh.log.dg.declaration",
                related_record_id=declaration.id,
                related_record_display=declaration.name,
                context={"from_state": current, "to_state": target_state},
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_dg_internal_state_write"):
            raise UserError(_(
                "[EHL-DG-DECL-001] State changes on a DG declaration "
                "must go through the action buttons. Direct writes are "
                "rejected."
            ))
        return super().write(vals)

    # ----- Pre-flight checks -----

    def _preflight_check_ready(self):
        for declaration in self:
            blockers = []
            if not declaration.line_ids:
                blockers.append(_("No UN lines on the declaration."))
            for line in declaration.line_ids:
                if line.net_quantity <= 0:
                    blockers.append(_(
                        "Line %(seq)s has zero net quantity."
                    ) % {"seq": line.sequence})
                if not line.packaging_description:
                    blockers.append(_(
                        "Line %(seq)s has no packaging description."
                    ) % {"seq": line.sequence})
            if not declaration.emergency_contact_phone:
                blockers.append(_("Emergency contact phone is required."))
            if blockers:
                raise EhLogValidationError(
                    133,
                    _(
                        "DG declaration %(name)s cannot be marked "
                        "ready. Resolve:\n\n- %(list)s"
                    ) % {
                        "name": declaration.name,
                        "list": "\n- ".join(blockers),
                    },
                )

    # ----- Actions -----

    def action_set_ready(self):
        self._preflight_check_ready()
        self._transition_state("ready")
        return True

    def action_issue(self):
        for declaration in self:
            declaration._transition_state("issued")
            declaration.issued_by_id = self.env.user
            declaration.issued_at = fields.Datetime.now()
        return True

    def action_back_to_draft(self):
        self._transition_state("draft")
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True
