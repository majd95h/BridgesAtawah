# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Subscription model: trackable target validation, milestone gating."""
from odoo.exceptions import UserError

from .common import EhLogTrackTestCase


class TestSubscription(EhLogTrackTestCase):

    def test_subscription_requires_trackable_model(self):
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.track.subscription"].create({
                "partner_id": self.customer.id,
                "res_model": "res.partner",
                "res_id": self.customer.id,
                "channel": "email",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-TRK-008]", str(ctx.exception))

    def test_subscription_rejects_unknown_model(self):
        with self.assertRaises(UserError) as ctx:
            self.env["eh.log.track.subscription"].create({
                "partner_id": self.customer.id,
                "res_model": "no.such.model",
                "res_id": 1,
                "channel": "email",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-TRK-007]", str(ctx.exception))

    def test_subscription_accepts_trackable_model(self):
        delivery = self._build_delivery()
        sub = self.env["eh.log.track.subscription"].create({
            "partner_id": self.customer.id,
            "res_model": "eh.log.last.mile.delivery",
            "res_id": delivery.id,
            "channel": "email",
            "company_id": self.company.id,
        })
        self.assertTrue(sub.id)
        self.assertEqual(sub.partner_id, self.customer)
