# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Trackable extension for the freight forwarding job.

Adds the trackable mixin and emits normalized events on each gated
state transition. Also exposes a tracking_reference field so an
inbound webhook can resolve a carrier-supplied identifier back to
the right job.
"""
from odoo import api, fields, models


# Map freight job states to seeded normalized event codes. The
# extension does not invent codes; it routes states to codes already
# defined in the event-code data file.
STATE_TO_EVENT_CODE = {
    "booked": "booked",
    "in_transit": "in_transit",
    "at_destination": "arrived",
    "delivered": "delivered",
    "closed": "closed",
    "cancelled": "cancelled",
}


class EhLogFreightJob(models.Model):
    _name = "eh.log.freight.job"
    _inherit = [
        "eh.log.freight.job",
        "eh.log.track.trackable",
    ]

    tracking_reference = fields.Char(
        string="Carrier Tracking Reference",
        help=(
            "External reference the carrier uses on inbound webhooks "
            "to identify this job. Populated when the booking comes "
            "back from the carrier with their reference."
        ),
        index=True,
    )

    def _transition_state(self, target_state: str):
        result = super()._transition_state(target_state)
        code = STATE_TO_EVENT_CODE.get(target_state)
        if code:
            for job in self:
                job.log_track_event(code)
        return result
