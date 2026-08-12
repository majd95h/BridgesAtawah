# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Deferment ledger entry: top-up credit, duty payment debit.

Linked back to the originating customs declaration for top-down
traceability. Manual entries are allowed for adjustments and
opening-balance corrections.
"""
from odoo import _, api, fields, models


ENTRY_KIND = [
    ("credit", "Credit (top-up)"),
    ("debit", "Debit (duty payment or adjustment)"),
]

ENTRY_STATE = [
    ("draft", "Draft"),
    ("posted", "Posted"),
    ("cancelled", "Cancelled"),
]


class EhLogCustomsDefermentEntry(models.Model):
    _name = "eh.log.customs.deferment.entry"
    _description = "Deferment Account Entry"
    _order = "entry_date desc, id desc"
    _rec_name = "description"

    account_id = fields.Many2one(
        "eh.log.customs.deferment.account",
        string="Deferment Account",
        required=True,
        ondelete="cascade",
        index=True,
    )

    entry_date = fields.Date(
        string="Entry Date",
        required=True,
        default=fields.Date.context_today,
        index=True,
    )

    entry_kind = fields.Selection(
        selection=ENTRY_KIND,
        string="Kind",
        required=True,
        index=True,
    )

    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
    )

    currency_id = fields.Many2one(
        related="account_id.currency_id",
        store=True,
        readonly=True,
    )

    description = fields.Char(
        string="Description",
        required=True,
    )

    declaration_id = fields.Many2one(
        "eh.log.customs.declaration",
        string="Customs Declaration",
        index=True,
        ondelete="set null",
        help="Set when the entry is auto-posted by a declaration "
             "submission. Empty for manual top-ups and adjustments.",
    )

    state = fields.Selection(
        selection=ENTRY_STATE,
        string="State",
        default="draft",
        required=True,
        index=True,
    )

    posted_at = fields.Datetime(string="Posted At", readonly=True, copy=False)

    company_id = fields.Many2one(
        related="account_id.company_id",
        store=True,
        index=True,
    )

    notes = fields.Text()

    def action_post(self):
        for entry in self:
            entry.write({
                "state": "posted",
                "posted_at": fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        for entry in self:
            entry.write({"state": "cancelled"})
        return True
