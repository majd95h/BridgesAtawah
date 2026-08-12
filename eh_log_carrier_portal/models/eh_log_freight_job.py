# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Freight job extension for carrier portal."""
from odoo import api, fields, models, _


class EhLogFreightJob(models.Model):
    _inherit = "eh.log.freight.job"

    carrier_booking_ids = fields.One2many(
        "eh.log.carrier.booking",
        "freight_job_id",
        string="Carrier Bookings",
    )
    carrier_booking_count = fields.Integer(
        string="Carrier Bookings",
        compute="_compute_carrier_booking_count",
    )

    def _compute_carrier_booking_count(self):
        for job in self:
            job.carrier_booking_count = len(job.carrier_booking_ids)

    def action_open_rate_shop(self):
        """Launch the rate-shop wizard pre-populated from the job."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Carrier Rate Shop"),
            "res_model": "eh.log.carrier.rate.shop.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_freight_job_id": self.id,
            },
        }

    def action_view_carrier_bookings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Carrier Bookings"),
            "res_model": "eh.log.carrier.booking",
            "view_mode": "list,form",
            "domain": [("freight_job_id", "=", self.id)],
            "context": {"default_freight_job_id": self.id},
        }
