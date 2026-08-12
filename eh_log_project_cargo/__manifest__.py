# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Project Cargo',
    'summary': 'A heavy-lift and project cargo module that captures the engineering and logistics of an oversized move in one gated, auditable job record, with project cargo, out-of-gauge (OOG), abnormal load, super-load, SPMT and modular trailer planning, crane and prime mover equipment master, multi-vehicle convoy assembly, road-authority and police escort permit register, route survey with bridge clearance and axle-load limits, and method statement, lift plan and permit application PDFs for Odoo 19 Community.',
    'description': 'Heavy-lift and project cargo for Odoo 19 Community. Manages oversized moves (turbines, transformers, refinery columns, modular plant) as a single gated job spine covering oversized items with automatic envelope flagging, a crane and trailer equipment master, multi-vehicle convoy plans, a permit register with expiry alerts, route surveys with clearance and axle-load limits, and three PDF documents. Built as the project-cargo extension of the ERP Heritage logistics suite. Multi-company isolation throughout.',
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
        'security/eh_log_project_cargo_security.xml',
        'security/eh_log_project_cargo_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_project_cargo_sequences.xml',
        'data/eh_log_project_cargo_data.xml',
        'data/eh_log_project_cargo_cron.xml',
        'report/eh_log_project_cargo_method_statement_report.xml',
        'report/eh_log_project_cargo_lift_plan_report.xml',
        'report/eh_log_project_cargo_permit_application_report.xml',
        'views/eh_log_project_cargo_equipment_views.xml',
        'views/eh_log_project_cargo_job_views.xml',
        'views/eh_log_project_cargo_item_views.xml',
        'views/eh_log_project_cargo_convoy_views.xml',
        'views/eh_log_project_cargo_permit_views.xml',
        'views/eh_log_project_cargo_route_survey_views.xml',
        'views/eh_log_project_cargo_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_project_cargo_search_views.xml',
        'views/sale_order_views.xml',
        'views/eh_log_project_cargo_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_project_cargo.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
