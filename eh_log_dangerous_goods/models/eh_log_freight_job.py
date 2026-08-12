# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Freight job extension: spawn DG declaration on creation when required."""
from odoo import _, api, fields, models


class EhLogFreightJob(models.Model):
    _inherit = "eh.log.freight.job"

    dg_declaration_ids = fields.One2many(
        "eh.log.dg.declaration",
        "freight_job_id",
        string="DG Declarations",
        copy=False,
    )

    dg_declaration_count = fields.Integer(
        string="DG Declarations",
        compute="_compute_dg_declaration_count",
    )

    @api.depends("dg_declaration_ids")
    def _compute_dg_declaration_count(self):
        for job in self:
            job.dg_declaration_count = len(job.dg_declaration_ids)

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        Declaration = self.env["eh.log.dg.declaration"].sudo()
        mode_map = {
            "sea": "sea",
            "air": "air",
            "road": "road",
            "rail": "rail",
            "multimodal": "multimodal",
            "courier": "air",
        }
        for job in jobs:
            order = job.sale_order_id
            if not order or not order.eh_log_dg_required:
                continue
            Declaration.create({
                "sale_order_id": order.id,
                "freight_job_id": job.id,
                "mode": mode_map.get(job.mode, "multimodal"),
                "company_id": job.company_id.id,
                "shipper_id": job.shipper_id.id or job.customer_id.id,
                "consignee_id": job.consignee_id.id or job.customer_id.id,
                "emergency_contact_name": _("To be set"),
                "emergency_contact_phone": _("To be set"),
            })
        return jobs

    def action_view_dg_declarations(self):
        self.ensure_one()
        if len(self.dg_declaration_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "eh.log.dg.declaration",
                "view_mode": "form",
                "res_id": self.dg_declaration_ids.id,
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("DG Declarations"),
            "res_model": "eh.log.dg.declaration",
            "view_mode": "list,form",
            "domain": [("freight_job_id", "=", self.id)],
            "context": {"default_freight_job_id": self.id},
        }
