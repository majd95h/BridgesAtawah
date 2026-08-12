# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""UN number format validation, normalisation, seed integrity."""
from psycopg2 import IntegrityError
from odoo.tools.misc import mute_logger

from odoo.addons.eh_log_base.exceptions import EhLogValidationError

from .common import EhLogDgTestCase


REQUIRED_UNS = [
    "UN1090", "UN1170", "UN1203", "UN1263", "UN1789", "UN1830",
    "UN1950", "UN1965", "UN1977", "UN2794", "UN3077", "UN3082",
    "UN3480", "UN3481", "UN3373", "UN2814",
]


class TestUnNumber(EhLogDgTestCase):

    def test_seed_un_numbers_present(self):
        UN = self.env["eh.log.dg.un.number"]
        for code in REQUIRED_UNS:
            record = UN.search([("un_number", "=", code)])
            self.assertEqual(
                len(record), 1,
                f"Seed UN number {code} missing or duplicated.",
            )

    def test_un_number_unique(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["eh.log.dg.un.number"].create({
                    "un_number": "UN1090",
                    "proper_shipping_name": "Duplicate Acetone",
                    "primary_class_id": self.env.ref(
                        "eh_log_dangerous_goods.dg_class_3"
                    ).id,
                    "packing_group": "II",
                })

    def test_un_number_format_validation(self):
        with self.assertRaises(EhLogValidationError) as ctx:
            self.env["eh.log.dg.un.number"].create({
                "un_number": "1090",  # missing 'UN' prefix
                "proper_shipping_name": "Bad",
                "primary_class_id": self.env.ref(
                    "eh_log_dangerous_goods.dg_class_3"
                ).id,
                "packing_group": "II",
            })
        self.assertIn("[EHL-BASE-130]", str(ctx.exception))

    def test_un_number_normalised_uppercase(self):
        record = self.env["eh.log.dg.un.number"].create({
            "un_number": " un9999 ",
            "proper_shipping_name": "Test substance",
            "primary_class_id": self.env.ref(
                "eh_log_dangerous_goods.dg_class_9"
            ).id,
            "packing_group": "III",
        })
        self.assertEqual(record.un_number, "UN9999")

    def test_marine_pollutant_flag_seeded(self):
        # UN3082 is a marine pollutant per the seed.
        un = self.env.ref("eh_log_dangerous_goods.un_3082")
        self.assertTrue(un.marine_pollutant)

    def test_iata_passenger_forbidden_seeded(self):
        # UN3480 (lithium ion batteries) is forbidden on passenger aircraft.
        un = self.env.ref("eh_log_dangerous_goods.un_3480")
        self.assertTrue(un.iata_passenger_aircraft_forbidden)
