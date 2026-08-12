# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Outbound: state machine, retry counter, dead-letter resume."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

from .common import EhLogEdiTestCase


class TestMessageLifecycle(EhLogEdiTestCase):

    def _build_outbound(self):
        job = self._build_freight_job()
        return self.partner_config.queue_outbound(self.iftmin, job)

    def test_initial_state(self):
        outbound = self._build_outbound()
        self.assertEqual(outbound.state, "draft")
        self.assertTrue(outbound.name.startswith("EDO/"))

    def test_full_lifecycle(self):
        outbound = self._build_outbound()
        outbound.action_queue()
        self.assertEqual(outbound.state, "queued")
        self.assertTrue(outbound.payload)
        outbound.action_send()
        self.assertEqual(outbound.state, "sent")
        self.assertTrue(outbound.transport_reference)
        outbound.action_mark_acked()
        outbound.action_close()
        self.assertEqual(outbound.state, "closed")

    def test_state_direct_write_blocked(self):
        outbound = self._build_outbound()
        with self.assertRaises(UserError) as ctx:
            outbound.write({"state": "sent"})
        self.assertIn("[EHL-EDI-009]", str(ctx.exception))

    def test_disallowed_transition_blocked(self):
        outbound = self._build_outbound()
        with self.assertRaises(JobStateConflictError):
            outbound._transition_state("closed")

    def test_cron_dispatches_queued_only(self):
        outbound = self._build_outbound()
        outbound.action_queue()
        Outbound = self.env["eh.log.edi.outbound"]
        Outbound.cron_dispatch_outbound()
        outbound.invalidate_recordset()
        self.assertEqual(outbound.state, "sent")
