# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Warehouse 3PL',
    'summary': 'Bonded warehouse and third-party logistics billing for Odoo 19 Community that turns every receipt, pick, and pallet-day into a defensible monthly invoice from an append-only movement log and immutable daily snapshots, covering 3PL billing, storage charges per pallet per day, handling in and handling out, rate cards, goods receipt notes, pick lists, storage statements, and warehouse customer billing runs.',
    'description': 'A 3PL and bonded warehouse billing module for Odoo 19 Community. It models space let to clients, applies per-client rate cards to handling and storage activity, and produces a monthly draft sale order from an audit trail of movements and nightly on-hand snapshots. Receipts and picks run on locked state machines, every billable activity lands in an append-only movement log, and storage is summed from immutable daily snapshots so the bill never depends on re-deriving history. Facility, zone, and location masters carry a customs status classification (bonded, free zone, transit, domestic) for reporting and segregation.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Warehouse',
    'version': '19.0.1.0.0',
    'depends': [
        'eh_log_base',
        'eh_log_quotation',
        'eh_log_freight',
        'sale_management',
        'product',
        'mail',
    ],
    'data': [
        'security/eh_log_warehouse_3pl_security.xml',
        'security/eh_log_warehouse_3pl_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_warehouse_3pl_sequences.xml',
        'data/eh_log_warehouse_3pl_cron.xml',
        'data/eh_log_warehouse_3pl_paperformat.xml',
        'report/eh_log_warehouse_grn_report.xml',
        'report/eh_log_warehouse_pick_list_report.xml',
        'report/eh_log_warehouse_storage_statement_report.xml',
        'views/eh_log_warehouse_facility_views.xml',
        'views/eh_log_warehouse_zone_views.xml',
        'views/eh_log_warehouse_location_views.xml',
        'views/eh_log_warehouse_client_views.xml',
        'views/eh_log_warehouse_rate_card_views.xml',
        'views/eh_log_warehouse_receipt_views.xml',
        'views/eh_log_warehouse_pick_views.xml',
        'views/eh_log_warehouse_movement_views.xml',
        'views/eh_log_warehouse_snapshot_views.xml',
        'views/eh_log_warehouse_billing_run_views.xml',
        'views/eh_log_warehouse_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_warehouse_search_views.xml',
        'views/sale_order_views.xml',
        'views/eh_log_warehouse_3pl_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_warehouse.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
