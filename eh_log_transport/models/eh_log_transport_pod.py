# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Electronic proof of delivery (ePOD).

Per-stop record of receipt: recipient name, signature image, time
stamp, optional GPS coordinates, optional photo. The driver app
captures these fields offline and syncs when connectivity returns
(driver app is a separate module; this base ships the data model).
"""
from odoo import _, api, fields, models


POD_STATUS = [
    ("captured", "Captured"),
    ("synced", "Synced from Driver App"),
    ("disputed", "Disputed"),
    ("voided", "Voided"),
]


class EhLogTransportPod(models.Model):
    _name = "eh.log.transport.pod"
    _description = "Electronic Proof of Delivery"
    _order = "trip_id, captured_at desc"
    _rec_name = "recipient_name"

    trip_id = fields.Many2one(
        "eh.log.transport.trip",
        string="Trip",
        required=True,
        ondelete="cascade",
        index=True,
    )

    recipient_name = fields.Char(
        string="Recipient Name",
        required=True,
    )

    recipient_role = fields.Char(string="Recipient Role")

    captured_at = fields.Datetime(
        string="Captured At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )

    signature_image = fields.Binary(
        string="Signature",
        attachment=True,
    )

    photo_image = fields.Binary(
        string="Photo",
        attachment=True,
    )

    gps_latitude = fields.Float(
        string="GPS Latitude",
        digits=(9, 6),
    )

    gps_longitude = fields.Float(
        string="GPS Longitude",
        digits=(9, 6),
    )

    notes = fields.Text(string="Notes")

    status = fields.Selection(
        selection=POD_STATUS,
        string="Status",
        default="captured",
        required=True,
        index=True,
    )

    company_id = fields.Many2one(
        related="trip_id.company_id",
        store=True,
        index=True,
    )

    @api.depends("recipient_name", "captured_at")
    def _compute_display_name(self):
        for record in self:
            ts = record.captured_at and record.captured_at.strftime("%Y-%m-%d %H:%M") or ""
            record.display_name = f"{record.recipient_name} ({ts})" if ts else record.recipient_name or _("ePOD")
