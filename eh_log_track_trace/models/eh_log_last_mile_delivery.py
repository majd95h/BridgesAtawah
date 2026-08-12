# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Trackable extension for the last-mile delivery stop.

The last-mile state machine has more granular outcomes than the
freight job. The map below routes the meaningful customer-facing
transitions to normalized event codes; failed and returned states
also fire so the public page surfaces the negative path.
"""
from odoo import fields, models


STATE_TO_EVENT_CODE = {
    "out_for_delivery": "out_for_delivery",
    "delivered": "delivered",
    "failed": "delivery_failed",
    "returned": "returned",
    "cancelled": "cancelled",
}


class EhLogLastMileDelivery(models.Model):
    _name = "eh.log.last.mile.delivery"
    _inherit = [
        "eh.log.last.mile.delivery",
        "eh.log.track.trackable",
    ]

    tracking_reference = fields.Char(
        string="External Tracking Reference",
        index=True,
    )

    def _transition_state(self, target_state: str):
        result = super()._transition_state(target_state)
        code = STATE_TO_EVENT_CODE.get(target_state)
        if code:
            for delivery in self:
                delivery.log_track_event(code)
        return result
