# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Logistics Dashboard',
    'summary': 'A single operational landing page for the ERP Heritage logistics suite that reads live counts from quotation, freight, customs, and transport on every form load and opens the underlying records pre-filtered on click. Logistics dashboard, freight forwarder dashboard, operational KPI tiles, single pane of glass, customs declaration tracker, transport trip monitor, COD outstanding, EDI dead-letter queue, weighted sales pipeline, Odoo 19 Community logistics dashboard, 3PL operations cockpit.',
    'description': 'An operational dashboard for the ERP Heritage logistics suite. It hard-depends on the base, quotation, freight, customs, and transport engines, and softly adapts to specialised verticals through env.get so a tile only appears when its module is installed. Every KPI is a live search_count, and every tile drills down to the source records pre-filtered. No snapshot caching, no scheduled jobs.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': [
        'eh_log_base',
        'eh_log_quotation',
        'eh_log_freight',
        'eh_log_customs',
        'eh_log_transport',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/eh_log_dashboard_views.xml',
        'views/eh_log_dashboard_pivot_graph_views.xml',
        'views/eh_log_dashboard_menus.xml',
    ],
    'assets': {
        'web.assets_backend': ['eh_log_dashboard/static/src/js/eh_log_dashboard_tour.js'],
    },
    'demo': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
