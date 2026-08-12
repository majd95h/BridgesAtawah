# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Last Mile',
    'summary': 'Last-mile distribution for Odoo 19 Community that runs the high-frequency B2C and B2B drop pattern as first-class records, covering wave planning, multi-stop dispatch, per-stop state machines, attempt logging, cash-on-delivery capture and end-of-shift cash-up, returns and return-to-sender, and a driver manifest PDF, with last mile delivery, route dispatch, ePOD, proof of delivery, COD collection, delivery attempts, failed delivery, returns management, driver manifest, and multi-company logistics.',
    'description': "Last-mile delivery management for Odoo 19 Community. Plan a driver's day as a wave of stops, dispatch the whole wave in one action, track each delivery through its own state machine, log every attempt, capture cash on delivery, handle failures and returns, and print a driver manifest with an end-of-shift cash-up table.",
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': ['eh_log_base', 'eh_log_quotation', 'eh_log_transport'],
    'data': [
        'security/eh_log_last_mile_security.xml',
        'security/eh_log_last_mile_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_last_mile_sequences.xml',
        'data/eh_log_last_mile_config_data.xml',
        'report/eh_log_last_mile_manifest_report.xml',
        'views/eh_log_last_mile_wave_views.xml',
        'views/eh_log_last_mile_delivery_views.xml',
        'views/eh_log_last_mile_attempt_views.xml',
        'views/eh_log_last_mile_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_last_mile_search_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/eh_log_last_mile_mass_action_views.xml',
        'views/eh_log_last_mile_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_last_mile.xml'],
    'images': ['static/description/banner.gif'],
    'assets': {
        'web.assets_backend': ['eh_log_last_mile/static/src/js/eh_log_last_mile_tour.js'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
