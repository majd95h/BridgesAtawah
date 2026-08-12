# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Partner configuration: defaults, identifier resolution."""
from odoo.exceptions import ValidationError

from .common import EhLogEdiTestCase


class TestPartnerConfig(EhLogEdiTestCase):

    def test_only_one_default_per_partner(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.edi.partner"].create({
                "name": "Second Default Config",
                "partner_id": self.partner.id,
                "partner_identifier": "EDI-PRT-002",
                "transport_id": self.transport.id,
                "is_default": True,
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-EDI-008]", str(ctx.exception))

    def test_self_identifier_override(self):
        self.partner_config.self_party_identifier_override = "OVERRIDE-001"
        self.assertEqual(
            self.partner_config._self_party_identifier(),
            "OVERRIDE-001",
        )

    def test_self_identifier_falls_back_to_param(self):
        Param = self.env["ir.config_parameter"].sudo()
        Param.set_param("eh_log_edi.self_identifier", "FROM-PARAM")
        self.assertEqual(
            self.partner_config._self_party_identifier(),
            "FROM-PARAM",
        )

    def test_smtp_transport_requires_email(self):
        with self.assertRaises(ValidationError) as ctx:
            self.env["eh.log.edi.transport"].create({
                "name": "Bad SMTP",
                "code": "BAD-SMTP",
                "protocol": "smtp",
                "company_id": self.company.id,
            })
        self.assertIn("[EHL-EDI-003]", str(ctx.exception))
