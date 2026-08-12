# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Freight job extension: queue IFTMIN on dispatch."""
from odoo import api, fields, models, _


class EhLogFreightJob(models.Model):
    _inherit = "eh.log.freight.job"

    eh_log_edi_outbound_count = fields.Integer(
        string="EDI Outbound Messages",
        compute="_compute_eh_log_edi_outbound_count",
    )

    def _compute_eh_log_edi_outbound_count(self):
        Outbound = self.env["eh.log.edi.outbound"]
        for job in self:
            job.eh_log_edi_outbound_count = Outbound.search_count([
                ("source_model", "=", self._name),
                ("source_id", "=", job.id),
            ])

    def action_view_edi_outbound(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("EDI Outbound"),
            "res_model": "eh.log.edi.outbound",
            "view_mode": "list,form",
            "domain": [
                ("source_model", "=", self._name),
                ("source_id", "=", self.id),
            ],
        }

    def action_queue_iftmin(self):
        """Queue an IFTMIN forwarding instruction per EDI partner."""
        self.ensure_one()
        Partner = self.env["eh.log.edi.partner"]
        MessageType = self.env["eh.log.edi.message.type"]
        iftmin = MessageType.search([("code", "=", "IFTMIN")], limit=1)
        if not iftmin:
            return False
        partners = Partner.search([
            ("active", "=", True),
            ("message_type_ids", "in", iftmin.id),
            ("company_id", "=", self.company_id.id),
        ])
        for partner_config in partners:
            partner_config.queue_outbound(iftmin, self)
        return True
