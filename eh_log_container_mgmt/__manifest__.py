# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Container Management',
    'summary': 'Container fleet operations for freight forwarders and 3PL operators, layered on the freight container record: depot master data, append-only gate-in and gate-out movements, maintenance and repair work orders with a guarded lifecycle, lease in and lease out contracts, per-container demurrage and detention against agreed free time, and an Equipment Interchange Receipt PDF, with container depot management, gate movement log, M and R work orders, container leasing, D and D charge calculation, free time tracking, EIR, container yard, ISO type, multi-company, Odoo 19 Community.',
    'description': 'Container fleet module for the ERP Heritage logistics suite. Models container depots, append-only gate movements, maintenance and repair work orders, lease in and out contracts, and per-container demurrage and detention against a configurable free time window, with an Equipment Interchange Receipt PDF. Built and runs on Odoo 19 Community.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': ['eh_log_base', 'eh_log_quotation', 'eh_log_freight'],
    'data': [
        'security/eh_log_container_mgmt_security.xml',
        'security/eh_log_container_mgmt_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_container_mgmt_sequences.xml',
        'data/eh_log_container_mgmt_cron.xml',
        'report/eh_log_container_mgmt_eir_report.xml',
        'views/eh_log_container_mgmt_depot_views.xml',
        'views/eh_log_container_mgmt_movement_views.xml',
        'views/eh_log_container_mgmt_work_order_views.xml',
        'views/eh_log_container_mgmt_lease_contract_views.xml',
        'views/eh_log_freight_container_views.xml',
        'views/eh_log_container_mgmt_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_container_mgmt.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
