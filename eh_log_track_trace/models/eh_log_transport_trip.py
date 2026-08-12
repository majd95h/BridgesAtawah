# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Trackable extension for the transport trip."""
from odoo import fields, models


STATE_TO_EVENT_CODE = {
    "dispatched": "dispatched",
    "at_pickup": "at_pickup",
    "in_transit": "in_transit",
    "at_delivery": "at_delivery",
    "delivered": "delivered",
    "closed": "closed",
    "cancelled": "cancelled",
}


class EhLogTransportTrip(models.Model):
    _name = "eh.log.transport.trip"
    _inherit = [
        "eh.log.transport.trip",
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
            for trip in self:
                trip.log_track_event(code)
        return result
