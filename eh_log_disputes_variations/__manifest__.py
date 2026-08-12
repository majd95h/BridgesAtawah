# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Disputes and Variations',
    'summary': 'Two related jobs in one install: a disputes desk for cargo claims and contested charges, and a variations desk for post-confirmation scope changes that write back to the linked sale order. Both attach to any operational record (sale order, freight job, transport trip, last-mile delivery, warehouse receipt or pick, ship disbursement account, container) through a validated polymorphic link, run a guarded state machine, and keep an append-only history. Search terms: freight forwarder disputes, cargo damage claims, demurrage dispute, short shipment claim, customs penalty dispute, change order, variation order, scope change, settlement letter, dispute notice PDF, Odoo 19 Community logistics, 3PL claims management.',
    'description': 'Dispute and variation management for the ERP Heritage logistics suite. A dispute records a customer-raised claim or contested charge against any operational record through a validated polymorphic link, runs a guarded state machine from opened through settled or written off, and keeps an append-only event log with locked fields. A variation records a post-confirmation scope change as priced lines that net to a delta, runs an approval workflow, and applies the change back to the linked sale order as new lines stored for later reversal. Ships eight seeded dispute categories, an SLA breach cron, three PDF documents, mass-settle and mass-write-off wizards, and per-company isolation. Built for Odoo 19 Community.',
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
        'security/eh_log_disputes_variations_security.xml',
        'security/eh_log_disputes_variations_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_disputes_variations_sequences.xml',
        'data/eh_log_disputes_variations_data.xml',
        'data/eh_log_disputes_variations_cron.xml',
        'report/eh_log_dispute_notice_report.xml',
        'report/eh_log_settlement_letter_report.xml',
        'report/eh_log_variation_order_report.xml',
        'views/eh_log_dispute_category_views.xml',
        'views/eh_log_dispute_views.xml',
        'views/eh_log_variation_views.xml',
        'views/eh_log_disputes_variations_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_disputes_variations_search_views.xml',
        'views/sale_order_views.xml',
        'views/eh_log_freight_job_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/eh_log_disputes_variations_mass_action_views.xml',
        'views/eh_log_disputes_variations_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_disputes.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
