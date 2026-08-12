# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Mass actions for disputes."""
from odoo import api, fields, models, _


class EhLogDisputeMassSettle(models.TransientModel):
    _name = "eh.log.dispute.mass.settle"
    _description = "Mass-settle Disputes"

    dispute_ids = fields.Many2many(
        "eh.log.dispute",
        string="Disputes",
        required=True,
    )
    use_offered_amount = fields.Boolean(
        string="Settle at Offered Amount",
        default=True,
        help=(
            "If ticked, each dispute settles at its currently offered "
            "amount. Disputes with no offered amount are skipped."
        ),
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            vals["dispute_ids"] = [(6, 0, active_ids)]
        return vals

    def action_apply(self):
        self.ensure_one()
        moved = self.env["eh.log.dispute"]
        skipped = self.env["eh.log.dispute"]
        for dispute in self.dispute_ids:
            try:
                if dispute.state == "offered":
                    dispute.action_accept_offer()
                if dispute.state == "accepted":
                    dispute.action_settle()
                    moved |= dispute
                else:
                    skipped |= dispute
            except Exception:
                skipped |= dispute
                continue
        return self.env["eh.log.dispute"]._notify_success(
            title=_("Mass-settle complete"),
            message=_(
                "Settled %(moved)d. Skipped %(skipped)d (wrong state)."
            ) % {"moved": len(moved), "skipped": len(skipped)},
        )


class EhLogDisputeMassWriteOff(models.TransientModel):
    _name = "eh.log.dispute.mass.write.off"
    _description = "Mass-write-off Disputes"

    dispute_ids = fields.Many2many(
        "eh.log.dispute",
        string="Disputes",
        required=True,
    )
    reason = fields.Text(
        string="Write-off Reason",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            vals["dispute_ids"] = [(6, 0, active_ids)]
        return vals

    def action_apply(self):
        self.ensure_one()
        moved = self.env["eh.log.dispute"]
        for dispute in self.dispute_ids:
            try:
                if dispute.state in ("escalated",):
                    dispute.action_write_off()
                    dispute.message_post(body=_(
                        "Mass write-off. Reason: %(reason)s"
                    ) % {"reason": self.reason})
                    moved |= dispute
            except Exception:
                continue
        return self.env["eh.log.dispute"]._notify_success(
            title=_("Mass write-off complete"),
            message=_("Wrote off %(count)d dispute(s).") % {
                "count": len(moved),
            },
        )
