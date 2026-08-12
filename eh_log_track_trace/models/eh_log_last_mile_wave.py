# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Trackable extension for the last-mile wave.

Waves are visible on the operator side of the public page but most
end-customer interest is at the per-delivery level. The wave still
gets tracking attached so dispatchers can hand a single URL to a
fleet manager and see all stops on one timeline.
"""
from odoo import fields, models


STATE_TO_EVENT_CODE = {
    "dispatched": "wave_dispatched",
    "in_progress": "wave_in_progress",
    "completed": "wave_completed",
    "closed": "closed",
    "cancelled": "cancelled",
}


class EhLogLastMileWave(models.Model):
    _name = "eh.log.last.mile.wave"
    _inherit = [
        "eh.log.last.mile.wave",
        "eh.log.track.trackable",
    ]

    tracking_reference = fields.Char(
        string="External Wave Reference",
        index=True,
    )

    def _transition_state(self, target_state: str):
        result = super()._transition_state(target_state)
        code = STATE_TO_EVENT_CODE.get(target_state)
        if code:
            for wave in self:
                wave.log_track_event(code)
        return result
