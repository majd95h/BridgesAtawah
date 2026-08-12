# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""HS code validation, level inference, seed integrity."""
from odoo.addons.eh_log_base.exceptions import EhLogValidationError

from .common import EhLogCustomsTestCase


REQUIRED_CHAPTERS = ["01", "22", "27", "30", "39", "44", "61", "62", "84", "85", "87", "94"]


class TestHsCode(EhLogCustomsTestCase):

    def test_seed_chapters_present(self):
        HS = self.env["eh.log.customs.hs.code"]
        for chapter in REQUIRED_CHAPTERS:
            record = HS.search([("code", "=", chapter)])
            self.assertTrue(
                record,
                f"Seed HS chapter {chapter} missing.",
            )

    def test_level_inferred_from_code_length(self):
        HS = self.env["eh.log.customs.hs.code"]
        chapter = HS.search([("code", "=", "85")], limit=1)
        self.assertEqual(chapter.level, "chapter")
        heading = HS.create({"code": "8517", "name": "Telephones"})
        self.assertEqual(heading.level, "heading")
        sub = HS.create({"code": "851712", "name": "Mobile phones"})
        self.assertEqual(sub.level, "subheading")
        national_8 = HS.create({"code": "85171211", "name": "5G handsets"})
        self.assertEqual(national_8.level, "national_8")

    def test_non_numeric_rejected(self):
        with self.assertRaises(EhLogValidationError) as ctx:
            self.env["eh.log.customs.hs.code"].create({
                "code": "85AB",
                "name": "Bad",
            })
        self.assertIn("[EHL-BASE-007]", str(ctx.exception))

    def test_invalid_length_rejected(self):
        with self.assertRaises(EhLogValidationError) as ctx:
            self.env["eh.log.customs.hs.code"].create({
                "code": "12345",
                "name": "Five digits not allowed",
            })
        self.assertIn("[EHL-BASE-008]", str(ctx.exception))

    def test_country_scope_allows_duplicate_code(self):
        HS = self.env["eh.log.customs.hs.code"]
        ae = self.env.ref("base.ae")
        sa = self.env.ref("base.sa")
        HS.create({"code": "85171234", "name": "AE detail", "country_id": ae.id})
        HS.create({"code": "85171234", "name": "SA detail", "country_id": sa.id})
        # No constraint violation expected.
        records = HS.search([("code", "=", "85171234")])
        self.assertEqual(len(records), 2)
