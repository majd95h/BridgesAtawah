# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Cold Chain',
    'summary': 'Temperature controlled cargo monitoring for the freight forwarding suite, pairing reusable cold chain profiles with a monitoring run on each freight job, append only time series readings, a sustained breach deviation detector, and a per run compliance certificate PDF, with search terms cold chain monitoring, pharma cold chain, GDP temperature excursion, reefer container monitoring, frozen and deep frozen cargo, chilled and controlled room, deviation detection, compliance certificate, Odoo 19 Community logistics.',
    'description': 'Cold chain temperature monitoring for the ERP Heritage logistics suite. Ships reusable temperature profiles (pharma, chilled, frozen, deep frozen, controlled room, dry ice), a guarded monitoring run attached to each freight job, append only readings, a sustained breach deviation detector with a resolution workflow, and a per run compliance certificate. Depends on the logistics base, quotation, and freight modules. Built and tested on Odoo 19 Community.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': ['eh_log_base', 'eh_log_quotation', 'eh_log_freight'],
    'data': [
        'security/eh_log_cold_chain_security.xml',
        'security/eh_log_cold_chain_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_cold_chain_sequences.xml',
        'data/eh_log_cold_chain_profile_data.xml',
        'report/eh_log_cold_chain_compliance_report.xml',
        'views/eh_log_cold_chain_profile_views.xml',
        'views/eh_log_cold_chain_run_views.xml',
        'views/eh_log_cold_chain_reading_views.xml',
        'views/eh_log_cold_chain_deviation_views.xml',
        'views/sale_order_views.xml',
        'views/eh_log_freight_job_views.xml',
        'views/eh_log_cold_chain_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_cold_chain.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
