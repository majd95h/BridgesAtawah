# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Dispute category master.

A category groups disputes for routing, default SLA, and reporting.
The seeded set covers the categories every freight forwarder
encounters; operators add custom categories for their lane.

The default_sla_days field drives the SLA breach cron: a dispute in
this category that has been opened longer than the configured days
without reaching settled / closed lights up on the dashboard.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EhLogDisputeCategory(models.Model):
    _name = "eh.log.dispute.category"
    _description = "Dispute Category"
    _order = "sequence, code"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True, size=12)
    sequence = fields.Integer(default=10)
    default_sla_days = fields.Integer(
        string="Default SLA Days",
        default=14,
        help=(
            "Days from open to expected resolution. The SLA cron "
            "flags disputes still open beyond this window. Operators "
            "can override per dispute."
        ),
    )
    requires_survey = fields.Boolean(
        string="Requires Survey",
        default=False,
        help=(
            "Cargo damage and loss categories typically need a "
            "survey before settlement; this flag drives the form "
            "to require an attached survey document."
        ),
    )
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _category_code_unique = models.Constraint(
        'unique(code)',
        'Dispute category code must be unique.',
    )

    def _is_seeded(self):
        self.ensure_one()
        return bool(self.env["ir.model.data"].search([
            ("model", "=", self._name),
            ("res_id", "=", self.id),
            ("module", "=", "eh_log_disputes_variations"),
        ], limit=1))

    def write(self, vals):
        if "code" in vals:
            for record in self:
                if record._is_seeded() and vals["code"] != record.code:
                    raise UserError(_(
                        "[EHL-DSP-001] Seeded dispute category "
                        "%(code)s cannot be renamed; create a new "
                        "category instead."
                    ) % {"code": record.code})
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record._is_seeded():
                raise UserError(_(
                    "[EHL-DSP-002] Seeded dispute category "
                    "%(code)s cannot be deleted; archive it instead."
                ) % {"code": record.code})
        return super().unlink()
