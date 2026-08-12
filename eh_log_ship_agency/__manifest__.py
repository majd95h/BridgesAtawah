# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Ship Agency',
    'summary': 'Ship agency operations for Odoo 19 Community: a validated vessel master, berth compatibility checks, an action-gated port call lifecycle, an append-only Statement of Facts, and a Disbursement Account that closes to a sale order. Search terms: ship agency, port agency, port call, vessel master, IMO number, MMSI, Statement of Facts, SOF, Disbursement Account, DA, proforma, husbandry services, Notice of Readiness, NOR, ship chandlery, bunker coordination, crew change, laytime evidence, maritime, freight forwarding, Odoo 19 Community ship agency.',
    'description': 'Ship agency module for Odoo 19 Community. Handles the vessel side of a port: a vessel master keyed on the IMO number with checksum validation, a berth master with draft and LOA compatibility checks, a port call state machine from expected through closed, an append-only Statement of Facts event log, a Disbursement Account with estimate, actual and variance that posts to a sale order on close, and a husbandry service catalog. Ships Notice of Readiness, Statement of Facts and Disbursement Account PDFs. Part of the ERP Heritage logistics suite.',
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
        'mail',
    ],
    'data': [
        'security/eh_log_ship_agency_security.xml',
        'security/eh_log_ship_agency_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_ship_agency_sequences.xml',
        'data/eh_log_ship_agency_data.xml',
        'report/eh_log_ship_sof_report.xml',
        'report/eh_log_ship_da_report.xml',
        'report/eh_log_ship_nor_report.xml',
        'views/eh_log_ship_vessel_views.xml',
        'views/eh_log_ship_berth_views.xml',
        'views/eh_log_ship_port_call_views.xml',
        'views/eh_log_ship_sof_event_views.xml',
        'views/eh_log_ship_disbursement_views.xml',
        'views/eh_log_ship_husbandry_views.xml',
        'views/eh_log_ship_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_ship_search_views.xml',
        'views/sale_order_views.xml',
        'views/eh_log_ship_agency_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_ship.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
