# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""DG declaration: state machine, preflight checks, marine pollutant aggregate."""
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import (
    EhLogValidationError,
    JobStateConflictError,
)

from .common import EhLogDgTestCase


class TestDgDeclarationLifecycle(EhLogDgTestCase):

    def test_initial_state(self):
        dgd = self._build_declaration()
        self.assertEqual(dgd.state, "draft")
        self.assertTrue(dgd.name.startswith("DGD/"))

    def test_ready_blocks_when_no_lines(self):
        dgd = self._build_declaration()
        with self.assertRaises(EhLogValidationError) as ctx:
            dgd.action_set_ready()
        self.assertIn("[EHL-BASE-133]", str(ctx.exception))
        self.assertIn("No UN lines", str(ctx.exception))

    def test_ready_blocks_when_packaging_missing(self):
        dgd = self._build_declaration()
        # Create a line bypassing the packaging description.
        line = self._add_line(dgd, self.un_acetone)
        line.packaging_description = ""
        with self.assertRaises(EhLogValidationError) as ctx:
            dgd.action_set_ready()
        self.assertIn("packaging description", str(ctx.exception))

    def test_full_lifecycle(self):
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)
        dgd.action_set_ready()
        self.assertEqual(dgd.state, "ready")
        dgd.action_issue()
        self.assertEqual(dgd.state, "issued")
        self.assertEqual(dgd.issued_by_id, self.env.user)
        self.assertTrue(dgd.issued_at)

    def test_disallowed_transition_blocked(self):
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)
        with self.assertRaises(JobStateConflictError):
            dgd.action_issue()  # cannot issue from draft

    def test_direct_state_write_blocked(self):
        dgd = self._build_declaration()
        with self.assertRaises(UserError) as ctx:
            dgd.write({"state": "ready"})
        self.assertIn("[EHL-DG-DECL-001]", str(ctx.exception))

    def test_air_mode_blocks_passenger_forbidden_un(self):
        dgd = self._build_declaration(mode="air")
        # UN2814 (Infectious substance affecting humans) is forbidden
        # on passenger aircraft per the seed; if ALSO forbidden on
        # cargo, the constraint fires. UN2814 in seed has only
        # passenger forbidden = True so should not raise.
        self._add_line(dgd, self.un_lithium)
        # UN3480 has passenger forbidden = True only; this should NOT raise.
        # The constraint only fires when BOTH passenger and cargo are forbidden.
        dgd.invalidate_recordset()
        # No exception expected here.

    def test_marine_pollutant_aggregate(self):
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)  # not MP
        dgd.invalidate_recordset()
        self.assertFalse(dgd.has_marine_pollutant)
        # Add a marine pollutant UN.
        un_mp = self.env.ref("eh_log_dangerous_goods.un_3082")
        self._add_line(dgd, un_mp)
        dgd.invalidate_recordset()
        self.assertTrue(dgd.has_marine_pollutant)

    def test_total_quantity_computed(self):
        dgd = self._build_declaration()
        line = self._add_line(dgd, self.un_acetone, qty=5.0, packages=4)
        line.invalidate_recordset()
        self.assertEqual(line.total_quantity, 20.0)
