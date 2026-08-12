# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Customs Broker',
    'summary': 'Customs broker workspace for Odoo 19 Community that carries the customs declaration from draft to cleared with hard state guards, HS-code classification, per-line duty and VAT, a deferment account ledger, and a regulator-of-record abstraction that country packs register adapters against, with keywords customs broker, customs clearance, customs declaration, HS code classification, harmonised system, tariff, duty and VAT calculation, deferment account, single window, freight forwarding, 3PL, multi-company, Odoo 19 logistics.',
    'description': 'Customs broker module for the ERP Heritage logistics suite. Runs the customs declaration lifecycle through a whitelisted state machine, classifies goods against a hierarchical HS-code model, computes per-line duty and VAT, tracks a prepaid deferment account ledger, and submits through a regulator-of-record adapter that country localisation packs register. Multi-company isolated, audit-logged, no silent fallbacks.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': [
        'eh_log_base',
        'eh_log_quotation',
        'eh_log_freight',
        'sale_management',
        'account',
    ],
    'data': [
        'security/eh_log_customs_security.xml',
        'security/eh_log_customs_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_customs_sequences.xml',
        'data/eh_log_customs_declaration_type_data.xml',
        'data/eh_log_customs_hs_chapter_data.xml',
        'views/eh_log_customs_declaration_type_views.xml',
        'views/eh_log_customs_hs_code_views.xml',
        'views/eh_log_customs_declaration_views.xml',
        'views/eh_log_customs_declaration_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_customs_declaration_search_views.xml',
        'views/eh_log_customs_deferment_views.xml',
        'views/eh_log_customs_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_customs.xml'],
    'images': ['static/description/banner.gif'],
    'assets': {
        'web.assets_backend': ['eh_log_customs/static/src/js/eh_log_customs_tour.js'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
