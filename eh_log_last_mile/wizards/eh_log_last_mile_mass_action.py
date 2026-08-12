# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Mass actions for last-mile waves and deliveries."""
from odoo import api, fields, models, _


class EhLogLastMileMassDispatch(models.TransientModel):
    _name = "eh.log.last.mile.mass.dispatch"
    _description = "Mass Dispatch Waves"

    wave_ids = fields.Many2many(
        "eh.log.last.mile.wave",
        relation="eh_log_lm_mass_dispatch_rel",
        column1="wizard_id",
        column2="wave_id",
        string="Waves",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            vals["wave_ids"] = [(6, 0, active_ids)]
        return vals

    def action_apply(self):
        self.ensure_one()
        moved = self.env["eh.log.last.mile.wave"]
        for wave in self.wave_ids:
            try:
                wave.action_dispatch()
                moved |= wave
            except Exception:
                continue
        return self.env["eh.log.last.mile.wave"]._notify_success(
            title=_("Dispatch complete"),
            message=_("%(count)d wave(s) dispatched.") % {
                "count": len(moved),
            },
        )


class EhLogLastMileMassMarkDelivered(models.TransientModel):
    _name = "eh.log.last.mile.mass.mark.delivered"
    _description = "Mass Mark Delivered"

    delivery_ids = fields.Many2many(
        "eh.log.last.mile.delivery",
        relation="eh_log_lm_mass_mark_deliv_rel",
        column1="wizard_id",
        column2="delivery_id",
        string="Deliveries",
        required=True,
    )
    recipient_name = fields.Char(
        string="Recipient Name",
        required=True,
        default="Bulk POD",
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            vals["delivery_ids"] = [(6, 0, active_ids)]
        return vals

    def action_apply(self):
        self.ensure_one()
        moved = self.env["eh.log.last.mile.delivery"]
        skipped = self.env["eh.log.last.mile.delivery"]
        for delivery in self.delivery_ids:
            if delivery.cod_amount:
                # COD deliveries cannot be bulk-closed without
                # collected amount; skip safely.
                skipped |= delivery
                continue
            try:
                delivery.action_mark_delivered(recipient_name=self.recipient_name)
                moved |= delivery
            except Exception:
                skipped |= delivery
                continue
        return self.env["eh.log.last.mile.delivery"]._notify_success(
            title=_("Mass mark delivered complete"),
            message=_(
                "Marked %(moved)d delivered. Skipped %(skipped)d "
                "(COD or wrong state)."
            ) % {"moved": len(moved), "skipped": len(skipped)},
        )
