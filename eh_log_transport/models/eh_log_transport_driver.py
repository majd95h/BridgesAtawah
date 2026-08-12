# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Lightweight driver master.

Linked to a ``res.partner`` so HR and contact details flow through
the standard contact record. The dedicated module attaches deeper
fields (license expiry tracking with chained activities, fatigue
limits, training records) when relevant.
"""
from odoo import _, api, fields, models


class EhLogTransportDriver(models.Model):
    _name = "eh.log.transport.driver"
    _description = "Transport Driver"
    _order = "name"
    _rec_names_search = ["name", "license_number"]

    name = fields.Char(
        string="Name",
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        index=True,
        help="Underlying contact record. Defaults to a new partner "
             "created on driver creation if left empty; reusing an "
             "existing partner is supported.",
    )

    license_number = fields.Char(string="License Number", index=True)

    license_class = fields.Char(string="License Class")

    license_expiry_date = fields.Date(
        string="License Expiry",
        help="Tracked so dispatchers do not assign an expired-license "
             "driver to a new trip. The dedicated KYC and HR modules "
             "automate the renewal activity.",
    )

    license_country_id = fields.Many2one(
        "res.country",
        string="License Country",
    )

    phone = fields.Char(string="Phone")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_transport_driver_company_rel",
        "driver_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    is_license_expired = fields.Boolean(
        string="License Expired",
        compute="_compute_is_license_expired",
        store=True,
    )

    notes = fields.Text(string="Notes")

    active = fields.Boolean(default=True)

    @api.depends("company_id")
    def _compute_company_ids(self):
        for driver in self:
            driver.company_ids = driver.company_id

    @api.depends("license_expiry_date")
    def _compute_is_license_expired(self):
        for driver in self:
            driver.is_license_expired = bool(
                driver.license_expiry_date
                and driver.license_expiry_date < fields.Date.context_today(driver)
            )

    @api.model_create_multi
    def create(self, vals_list):
        Partner = self.env["res.partner"]
        for vals in vals_list:
            if not vals.get("partner_id"):
                partner = Partner.create({
                    "name": vals.get("name"),
                    "phone": vals.get("phone") or False,
                })
                vals["partner_id"] = partner.id
        return super().create(vals_list)
