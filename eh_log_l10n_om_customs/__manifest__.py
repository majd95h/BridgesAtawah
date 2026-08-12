# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Logistics Oman Customs',
    'summary': 'eh_log_l10n_om_customs is the Sultanate of Oman customs add-on for the ERP Heritage logistics suite. It ships a concrete Bayan adapter (the Royal Oman Police Customs single window) speaking the documented JSON contract for declaration submission and status, seeds seven Oman-scoped declaration types and a starter set of Oman HS tariff overlays at the 5 percent VAT baseline, and seeds a mock-mode regulator profile so a fresh install runs end to end with zero network. The adapter inherits the suite engine: retry with backoff, a circuit breaker, an append-only audit message log with header redaction, per-company credential precedence, and API version pinning. Search terms: Oman customs Odoo, Bayan single window, Royal Oman Police Customs, GCC customs declaration, freight forwarder customs broker software, HS code tariff, customs deferment, Odoo 19 logistics, 3PL customs integration.',
    'description': 'Oman customs add-on for the ERP Heritage logistics suite. Ships a Bayan (Royal Oman Police Customs single window) JSON adapter for declaration submit and status, seven Oman declaration types, Oman HS tariff overlays, and a mock-mode regulator profile. Auto-installs when both the customs engine and the Oman localisation pack are present.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': ['eh_log_base', 'eh_log_customs', 'eh_log_l10n_om'],
    'data': [
        'security/ir.model.access.csv',
        'data/eh_log_l10n_om_customs_declaration_types_data.xml',
        'data/eh_log_l10n_om_customs_hs_codes_data.xml',
        'data/eh_log_l10n_om_customs_adapter_profile_data.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': True,
}
