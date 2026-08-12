# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Road Transport',
    'summary': 'Road transport dispatch for Odoo 19 Community that turns a delivery into a governed trip from planned through dispatched, at pickup, in transit, at delivery, delivered, and closed, with vehicle and driver masters, a license-expiry guard at dispatch, per-stop electronic proof of delivery, and an automatic demurrage and detention calculation off planned versus actual times. Road transport, trip planning, dispatch board, truck dispatch, ePOD, electronic proof of delivery, demurrage, detention, free time, driver license expiry, vehicle master, fleet, multi company logistics, Odoo 19 Community road logistics.',
    'description': 'Road transport dispatch module for the ERP Heritage logistics suite on Odoo 19 Community. Models the road leg as a trip with a guarded lifecycle, vehicle and driver masters, electronic proof of delivery, and an automatic detention calculation. Direct state writes are blocked and dispatch is gated on driver license, resources, and planned times.',
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
    ],
    'data': [
        'security/eh_log_transport_security.xml',
        'security/eh_log_transport_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_transport_sequences.xml',
        'views/eh_log_transport_vehicle_views.xml',
        'views/eh_log_transport_driver_views.xml',
        'views/eh_log_transport_trip_views.xml',
        'views/eh_log_transport_trip_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_transport_trip_search_views.xml',
        'views/eh_log_transport_menus.xml',
    ],
    'demo': ['demo/eh_log_demo_transport.xml'],
    'images': ['static/description/banner.gif'],
    'assets': {
        'web.assets_backend': ['eh_log_transport/static/src/js/eh_log_transport_tour.js'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
