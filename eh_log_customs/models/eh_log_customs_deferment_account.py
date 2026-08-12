# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Deferment account: broker's prepaid float at a customs authority.

One row per (broker company, regulator profile, currency). Live
balance is computed from deferment entries (positive top-ups versus
negative duty payments and adjustments). A configurable low-balance
threshold raises a warning activity to the account owner so the
broker can top up before a declaration is blocked at submission.
"""
from odoo import _, api, fields, models


class EhLogCustomsDefermentAccount(models.Model):
    _name = "eh.log.customs.deferment.account"
    _description = "Customs Deferment Account"
    _order = "company_id, regulator_profile_id"
    _rec_names_search = ["account_number", "name"]
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
        help="Operator-friendly label (e.g. 'Mirsal Deferment, Acme "
             "Logistics LLC, AED').",
    )

    account_number = fields.Char(
        string="Account Number",
        required=True,
        index=True,
        tracking=True,
        help="Account number issued by the customs authority.",
    )

    regulator_profile_id = fields.Many2one(
        "eh.log.adapter.profile",
        string="Regulator Profile",
        required=True,
        domain=[("provider_kind", "=", "regulator")],
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
        "eh_log_customs_deferment_account_company_rel",
        "account_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    opening_balance = fields.Monetary(
        string="Opening Balance",
        currency_field="currency_id",
        tracking=True,
    )

    entry_ids = fields.One2many(
        "eh.log.customs.deferment.entry",
        "account_id",
        string="Entries",
    )

    current_balance = fields.Monetary(
        string="Current Balance",
        currency_field="currency_id",
        compute="_compute_balance",
        store=True,
    )

    low_balance_threshold = fields.Monetary(
        string="Low Balance Threshold",
        currency_field="currency_id",
        help="When current balance drops below this value, a warning "
             "activity is raised to the account owner.",
    )

    is_low = fields.Boolean(
        string="Low",
        compute="_compute_is_low",
        store=True,
    )

    notes = fields.Text(string="Notes")

    active = fields.Boolean(default=True)

    _account_number_per_company_unique = models.Constraint(
        'UNIQUE(account_number, regulator_profile_id, company_id)',
        'Deferment account number must be unique per (regulator, company).',
    )

    @api.depends("company_id")
    def _compute_company_ids(self):
        for account in self:
            account.company_ids = account.company_id

    @api.depends(
        "opening_balance",
        "entry_ids", "entry_ids.amount", "entry_ids.entry_kind", "entry_ids.state",
    )
    def _compute_balance(self):
        for account in self:
            balance = account.opening_balance or 0.0
            for entry in account.entry_ids:
                if entry.state == "cancelled":
                    continue
                if entry.entry_kind == "credit":
                    balance += entry.amount
                else:
                    balance -= entry.amount
            account.current_balance = balance

    @api.depends("current_balance", "low_balance_threshold")
    def _compute_is_low(self):
        for account in self:
            account.is_low = bool(
                account.low_balance_threshold
                and account.current_balance < account.low_balance_threshold
            )
