# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Oman Logistics Suite',
    'summary': 'One installable that brings the complete ERP Heritage logistics stack onto an Oman Odoo 19 Community database, seventeen freight and customs and transport engines plus Oman master data and the Bayan customs adapter, all on a single version stream. Covers Oman logistics, Oman freight forwarding, customs broker, Bayan single window, Sohar Salalah Duqm ports, road transport, container management, dangerous goods IMDG segregation, cold chain, project cargo, ship agency, last mile, 3PL warehouse billing, EDI, track and trace, Odoo 19 Community.',
    'description': 'A dependency bundle that installs the ERP Heritage logistics suite scoped to the Sultanate of Oman in one step. It pulls in nineteen modules: the freight forwarding job file with cost versus revenue margin, customs declarations with duty and VAT and deferment guards, road transport, container management, cold chain, dangerous goods segregation, project cargo, ship agency, last mile, 3PL warehouse billing, an EDI outbound queue, signed carrier track and trace, a quotation costing layer, and a dashboard. On top it adds Oman ports, airports, customs offices, and free zones as master data, plus a Bayan single window customs adapter. This module ships no models of its own. It exists so an Oman operator installs and version-aligns the whole line under one publisher instead of nineteen separate searches.',
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
        'eh_log_dashboard',
        'eh_log_carrier_portal',
        'eh_log_cold_chain',
        'eh_log_container_mgmt',
        'eh_log_dangerous_goods',
        'eh_log_disputes_variations',
        'eh_log_edi',
        'eh_log_last_mile',
        'eh_log_project_cargo',
        'eh_log_ship_agency',
        'eh_log_track_trace',
        'eh_log_warehouse_3pl',
        'eh_log_l10n_om',
        'eh_log_l10n_om_customs',
    ],
    'data': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
