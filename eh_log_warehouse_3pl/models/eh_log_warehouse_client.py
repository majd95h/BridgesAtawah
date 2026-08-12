# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""3PL client master.

A client is a partner who has signed a storage and handling agreement
with the operator. The client points at one rate card; the rate card
defines the per-service prices used by the monthly billing run.

Clients see their own stock only. The portal-side scoping rule
filters all warehouse records by client_id when the requesting user
belongs to a portal partner; internal users see all clients (subject
to the company-isolation rule).
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EhLogWarehouseClient(models.Model):
    _name = "eh.log.warehouse.client"
    _description = "3PL Client"
    _order = "code"
    _rec_names_search = ["name", "code"]
    _inherit = ["mail.thread"]

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, size=12, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="restrict",
        tracking=True,
        help=(
            "Billing and shipping partner. The monthly billing run "
            "raises a sale order against this partner."
        ),
    )
    rate_card_id = fields.Many2one(
        "eh.log.warehouse.rate.card",
        string="Rate Card",
        required=True,
        ondelete="restrict",
        tracking=True,
        help=(
            "Active rate card. Changing the rate card affects bills "
            "raised after the change date; historic snapshots and "
            "movements stay linked to the rate card in force at that "
            "time through the billing line audit."
        ),
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    billing_day = fields.Integer(
        string="Billing Day",
        default=1,
        help=(
            "Day of the month the periodic billing run targets. The "
            "run cron checks this field; clients on different days "
            "let billing load be spread across the month."
        ),
    )
    storage_charging_basis = fields.Selection(
        [
            ("snapshot_average", "Average of Daily Snapshots"),
            ("snapshot_peak", "Peak of Daily Snapshots"),
            ("snapshot_first_of_month", "First-of-Month Snapshot"),
        ],
        string="Storage Basis",
        required=True,
        default="snapshot_average",
        help=(
            "How storage charges are derived from the snapshot "
            "history. Average is the industry default; peak is a "
            "punitive option used for surge-pricing contracts."
        ),
    )
    facility_ids = fields.Many2many(
        "eh.log.warehouse.facility",
        "eh_log_warehouse_client_facility_rel",
        "client_id",
        "facility_id",
        string="Facilities",
        help=(
            "Facilities the client may store in. Receipts and picks "
            "are restricted to this set."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _client_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Client code must be unique per company.',
    )

    @api.constrains("billing_day")
    def _check_billing_day(self):
        for client in self:
            if not 1 <= client.billing_day <= 28:
                raise ValidationError(_(
                    "[EHL-WHS-004] Billing day %(day)s must be "
                    "between 1 and 28 so the cron fires every "
                    "month."
                ) % {"day": client.billing_day})

    def _check_facility_allowed(self, facility):
        self.ensure_one()
        if self.facility_ids and facility not in self.facility_ids:
            raise UserError(_(
                "[EHL-WHS-005] Facility %(facility)s is not in "
                "client %(client)s's allowed facilities list."
            ) % {
                "facility": facility.display_name,
                "client": self.display_name,
            })
