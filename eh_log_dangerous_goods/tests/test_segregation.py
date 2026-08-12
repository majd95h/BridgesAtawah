# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Segregation detector: pair detection, single-class compatibility."""
from .common import EhLogDgTestCase


class TestSegregation(EhLogDgTestCase):

    def test_single_line_is_compatible(self):
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)
        dgd.invalidate_recordset()
        self.assertEqual(dgd.segregation_status, "ok")

    def test_no_lines_is_not_assessed(self):
        dgd = self._build_declaration()
        dgd.invalidate_recordset()
        self.assertEqual(dgd.segregation_status, "not_assessed")

    def test_class_3_with_class_8_flags_warning(self):
        # Per seed, class 3 (Flammable Liquid) is incompatible with
        # class 8 (Corrosive). Acetone (3) + sulphuric acid (8) should
        # trigger a warning.
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)
        self._add_line(dgd, self.un_h2so4)
        dgd.invalidate_recordset()
        self.assertEqual(dgd.segregation_status, "warning")
        self.assertIn("3", dgd.segregation_summary)
        self.assertIn("8", dgd.segregation_summary)

    def test_class_2_1_with_class_2_2_compatible(self):
        # Flammable gas + non-flammable gas: not in the seed
        # incompatibility list, so should be compatible.
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_lpg)
        un_n2 = self.env.ref("eh_log_dangerous_goods.un_1977")
        self._add_line(dgd, un_n2)
        dgd.invalidate_recordset()
        self.assertEqual(dgd.segregation_status, "ok")

    def test_same_class_multiple_lines_compatible(self):
        # Two flammable liquid lines: same class, no incompatibility.
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)
        un_ethanol = self.env.ref("eh_log_dangerous_goods.un_1170")
        self._add_line(dgd, un_ethanol)
        dgd.invalidate_recordset()
        self.assertEqual(dgd.segregation_status, "ok")

    def test_summary_lists_pair_once(self):
        # If both lines reference each other's incompatibility, the
        # summary should still list the pair only once.
        dgd = self._build_declaration()
        self._add_line(dgd, self.un_acetone)  # class 3
        self._add_line(dgd, self.un_h2so4)  # class 8
        dgd.invalidate_recordset()
        # Count how many times the warning line about class 3 vs 8 appears.
        summary = dgd.segregation_summary or ""
        self.assertEqual(
            summary.count("Class 3"), 1,
            "Class 3 pair should appear exactly once in the summary, "
            "not duplicated from both directions.",
        )
