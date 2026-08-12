# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Freight job extension: spawn the cold chain run on creation."""
from odoo import _, api, fields, models


class EhLogFreightJob(models.Model):
    _inherit = "eh.log.freight.job"

    cold_chain_run_ids = fields.One2many(
        "eh.log.cold.chain.run",
        "freight_job_id",
        string="Cold Chain Runs",
        copy=False,
    )

    cold_chain_run_count = fields.Integer(
        string="Cold Chain Runs",
        compute="_compute_cold_chain_run_count",
    )

    @api.depends("cold_chain_run_ids")
    def _compute_cold_chain_run_count(self):
        for job in self:
            job.cold_chain_run_count = len(job.cold_chain_run_ids)

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        Run = self.env["eh.log.cold.chain.run"].sudo()
        for job in jobs:
            order = job.sale_order_id
            if not order or not order.eh_log_cold_chain_required:
                continue
            if not order.eh_log_cold_chain_profile_id:
                # Required but no profile picked: skip auto-spawn so the
                # operator picks a profile and creates the run manually.
                # Posted as a chatter note for visibility.
                job.message_post(body=_(
                    "Cold chain monitoring required on the source order "
                    "but no profile selected. Create the cold chain run "
                    "manually under the Cold Chain tab."
                ))
                continue
            Run.create({
                "freight_job_id": job.id,
                "profile_id": order.eh_log_cold_chain_profile_id.id,
                "company_id": job.company_id.id,
            })
        return jobs

    def action_view_cold_chain_runs(self):
        self.ensure_one()
        if len(self.cold_chain_run_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "eh.log.cold.chain.run",
                "view_mode": "form",
                "res_id": self.cold_chain_run_ids.id,
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Cold Chain Runs"),
            "res_model": "eh.log.cold.chain.run",
            "view_mode": "list,form",
            "domain": [("freight_job_id", "=", self.id)],
            "context": {"default_freight_job_id": self.id},
        }
