# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Dangerous Goods',
    'summary': "Dangerous-goods declaration module for the ERP Heritage logistics suite that turns a freight job into a mode-correct shipper's declaration, with a UN number master, a nine-class hazard catalogue, a segregation incompatibility detector, and a printable Shipper's Declaration PDF. Dangerous goods, IMDG, IATA DGR, ADR, RID, UN number, hazard class, packing group, segregation, marine pollutant, lithium battery, hazmat freight forwarding, Odoo 19 Community.",
    'description': "Dangerous-goods declarations for sea, air, road, and rail freight on Odoo 19 Community. Carries a UN number master with UN1234 format validation, a hazard class catalogue with configurable incompatibility links, a per-shipment declaration whose mode drives the printed form, a segregation detector that flags incompatible class pairs, a marine-pollutant aggregate, an air guard that blocks UN numbers forbidden on both passenger and cargo aircraft, and a Shipper's Declaration PDF. Pairs with the Freight Forwarding module so a sale order flagged as dangerous spawns the declaration automatically.",
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': ['eh_log_base', 'eh_log_quotation', 'eh_log_freight'],
    'data': [
        'security/eh_log_dangerous_goods_security.xml',
        'security/eh_log_dangerous_goods_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_dangerous_goods_sequences.xml',
        'data/eh_log_dg_class_data.xml',
        'data/eh_log_dg_un_number_data.xml',
        'report/eh_log_dg_declaration_report.xml',
        'views/eh_log_dg_class_views.xml',
        'views/eh_log_dg_un_number_views.xml',
        'views/eh_log_dg_declaration_views.xml',
        'views/sale_order_views.xml',
        'views/eh_log_freight_job_views.xml',
        'views/eh_log_dangerous_goods_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_dg.xml'],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
