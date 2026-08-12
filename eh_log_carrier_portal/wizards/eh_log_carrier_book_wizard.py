# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Book wizard.

Confirm-and-book wizard launched from a quote line. Wraps the
booking creation so the operator can attach a freight job and a
free-text note before the carrier-side call goes out.
"""
from odoo import fields, models, _


class EhLogCarrierBookWizard(models.TransientModel):
    _name = "eh.log.carrier.book.wizard"
    _description = "Book Carrier Wizard"

    quote_id = fields.Many2one(
        "eh.log.carrier.rate.quote",
        string="Quote",
        required=True,
    )
    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
    )
    note = fields.Text(string="Internal Note")

    def action_book(self):
        self.ensure_one()
        Booking = self.env["eh.log.carrier.booking"]
        booking = Booking.create({
            "quote_id": self.quote_id.id,
            "freight_job_id": self.freight_job_id.id or False,
            "company_id": self.env.company.id,
        })
        if self.note:
            booking.message_post(body=self.note)
        booking.action_request()
        return {
            "type": "ir.actions.act_window",
            "name": _("Carrier Booking"),
            "res_model": "eh.log.carrier.booking",
            "view_mode": "form",
            "res_id": booking.id,
            "target": "current",
        }
