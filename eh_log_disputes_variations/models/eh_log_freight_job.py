# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Freight job: dispute / variation count + drill-down."""
from odoo import api, fields, models, _


class EhLogFreightJob(models.Model):
    _inherit = "eh.log.freight.job"

    eh_log_dispute_count = fields.Integer(
        string="Disputes",
        compute="_compute_dispute_variation_counts",
    )
    eh_log_variation_count = fields.Integer(
        string="Variations",
        compute="_compute_dispute_variation_counts",
    )

    def _compute_dispute_variation_counts(self):
        Dispute = self.env["eh.log.dispute"]
        Variation = self.env["eh.log.variation"]
        for job in self:
            job.eh_log_dispute_count = Dispute.search_count([
                ("res_model", "=", "eh.log.freight.job"),
                ("res_id", "=", job.id),
            ])
            job.eh_log_variation_count = Variation.search_count([
                ("res_model", "=", "eh.log.freight.job"),
                ("res_id", "=", job.id),
            ])

    def action_view_disputes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Disputes"),
            "res_model": "eh.log.dispute",
            "view_mode": "list,form",
            "domain": [
                ("res_model", "=", "eh.log.freight.job"),
                ("res_id", "=", self.id),
            ],
            "context": {
                "default_res_model": "eh.log.freight.job",
                "default_res_id": self.id,
                "default_customer_id": self.customer_id.id,
            },
        }

    def action_view_variations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Variations"),
            "res_model": "eh.log.variation",
            "view_mode": "list,form",
            "domain": [
                ("res_model", "=", "eh.log.freight.job"),
                ("res_id", "=", self.id),
            ],
            "context": {
                "default_res_model": "eh.log.freight.job",
                "default_res_id": self.id,
                "default_customer_id": self.customer_id.id,
            },
        }
