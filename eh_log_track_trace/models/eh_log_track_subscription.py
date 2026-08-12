# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Per-record notification subscriptions.

A subscription pairs a partner with a tracked record and a set of
event codes the partner cares about. The event-write path enumerates
matching subscriptions and queues outbound mail.

Subscriptions are usually self-served by the customer through the
public page (post-MVP) but can also be created internally by an ops
user on behalf of a partner.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EhLogTrackSubscription(models.Model):
    _name = "eh.log.track.subscription"
    _description = "Tracking Notification Subscription"
    _order = "create_date desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        "res.partner",
        string="Subscriber",
        required=True,
        ondelete="cascade",
        index=True,
    )
    res_model = fields.Char(
        string="Source Model",
        required=True,
        index=True,
    )
    res_id = fields.Integer(
        string="Source ID",
        required=True,
        index=True,
    )
    event_code_ids = fields.Many2many(
        "eh.log.track.event.code",
        "eh_log_track_sub_code_rel",
        "subscription_id",
        "code_id",
        string="Event Codes",
        help=(
            "If empty, all milestone events on the record trigger a "
            "notification. If populated, only events matching one of "
            "the listed codes trigger."
        ),
    )
    channel = fields.Selection(
        [
            ("email", "Email"),
            ("portal", "Portal Only"),
        ],
        string="Channel",
        default="email",
        required=True,
        help=(
            "Email queues an outbound mail per matching event. "
            "Portal-only suppresses outbound mail; the partner sees "
            "events on the public page only."
        ),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)
    display_name = fields.Char(
        compute="_compute_display_name",
        store=False,
    )

    _subscription_unique = models.Constraint(
        'unique(partner_id, res_model, res_id, channel)',
        'Duplicate subscription for the same partner, record, and channel.',
    )

    @api.depends("partner_id", "res_model", "res_id")
    def _compute_display_name(self):
        for sub in self:
            sub.display_name = "%s @ %s/%s" % (
                sub.partner_id.display_name or _("Unknown"),
                sub.res_model or "",
                sub.res_id or 0,
            )

    @api.constrains("res_model")
    def _check_res_model_is_trackable(self):
        for sub in self:
            Model = self.env.get(sub.res_model)
            if Model is None:
                raise UserError(_(
                    "[EHL-TRK-007] Subscription source model "
                    "%(model)s does not exist."
                ) % {"model": sub.res_model})
            if "eh.log.track.trackable" not in (Model._inherit or []):
                raise UserError(_(
                    "[EHL-TRK-008] Source model %(model)s is not "
                    "trackable; it must inherit "
                    "eh.log.track.trackable to be subscribed to."
                ) % {"model": sub.res_model})
