# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Carrier Portal',
    'summary': 'Outbound carrier connectivity for the ERP Heritage logistics suite: shop rates across every configured carrier in one pass, persist the quotes for audit, turn the chosen quote into a guarded booking, and poll the carrier for status until handoff. Two mock providers (ocean and air) ship as working reference adapters. Carrier portal, rate shopping, ocean and air freight booking, carrier integration adapter framework, freight forwarder quote comparison, transit-time ranking, booking lifecycle, Odoo 19 Community logistics.',
    'description': 'A carrier-side connector layer for freight forwarders and 3PLs on Odoo 19 Community. Register a carrier profile per company, constrain it to the lanes it serves, then run a rate-shop request that fans out across matching carriers and ranks the returned quotes by cheapest, fastest, balanced, or preferred. The chosen quote becomes a booking with a guarded state machine and a configurable cancellation window. A cron polls accepted and confirmed bookings for carrier-side status. Two mock adapters (ocean and air) ship as working templates for real provider integrations.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': [
        'eh_log_base',
        'eh_log_freight',
        'eh_log_quotation',
        'mail',
    ],
    'data': [
        'security/eh_log_carrier_portal_security.xml',
        'security/eh_log_carrier_portal_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_carrier_portal_sequences.xml',
        'data/eh_log_carrier_portal_cron.xml',
        'data/eh_log_carrier_portal_config_data.xml',
        'report/eh_log_carrier_booking_report.xml',
        'wizards/eh_log_carrier_rate_shop_wizard_views.xml',
        'wizards/eh_log_carrier_book_wizard_views.xml',
        'views/eh_log_carrier_profile_views.xml',
        'views/eh_log_carrier_lane_views.xml',
        'views/eh_log_carrier_rate_request_views.xml',
        'views/eh_log_carrier_booking_views.xml',
        'views/eh_log_carrier_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_carrier_search_views.xml',
        'views/eh_log_freight_job_views.xml',
        'views/res_config_settings_views.xml',
        'views/eh_log_carrier_portal_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_carrier.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
