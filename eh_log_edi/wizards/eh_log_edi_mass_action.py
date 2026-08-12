# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Mass actions for EDI queues."""
from odoo import api, fields, models, _


class EhLogEdiOutboundMassResume(models.TransientModel):
    _name = "eh.log.edi.outbound.mass.resume"
    _description = "Mass-resume EDI Dead-letter"

    outbound_ids = fields.Many2many(
        "eh.log.edi.outbound",
        string="Dead-letter Messages",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            vals["outbound_ids"] = [(6, 0, active_ids)]
        return vals

    def action_apply(self):
        self.ensure_one()
        moved = self.env["eh.log.edi.outbound"]
        for outbound in self.outbound_ids:
            if outbound.state == "dead_letter":
                outbound.action_resume_dead_letter()
                moved |= outbound
        return self.env["eh.log.edi.outbound"]._notify_success(
            title=_("Mass-resume complete"),
            message=_("%(count)d dead-letter message(s) re-queued.") % {
                "count": len(moved),
            },
        )


class EhLogEdiInboundMassReprocess(models.TransientModel):
    _name = "eh.log.edi.inbound.mass.reprocess"
    _description = "Mass-reprocess EDI Inbound"

    inbound_ids = fields.Many2many(
        "eh.log.edi.inbound",
        string="Inbound Messages",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            vals["inbound_ids"] = [(6, 0, active_ids)]
        return vals

    def action_apply(self):
        self.ensure_one()
        moved = self.env["eh.log.edi.inbound"]
        for inbound in self.inbound_ids:
            try:
                if inbound.state == "rejected":
                    inbound.action_resume()
                inbound.action_parse()
                if inbound.state == "parsed":
                    inbound.action_process()
                moved |= inbound
            except Exception:
                continue
        return self.env["eh.log.edi.inbound"]._notify_success(
            title=_("Mass-reprocess complete"),
            message=_("%(count)d inbound message(s) reprocessed.") % {
                "count": len(moved),
            },
        )
