# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Logistics Oman',
    'summary': 'Oman localisation pack that preloads the country reference data freight forwarders and 3PL operators need on day one, covering Sohar, Salalah, Sultan Qaboos (Muscat), Duqm and Khasab sea ports with UN/LOCODE references, Muscat, Salalah, Khasab, Duqm and Sohar airports with IATA and ICAO codes, the Royal Oman Police Customs Department and Oman Tax Authority with per-port and per-airport customs houses, and the Sohar, Salalah, Duqm (SEZAD) and Al Mazunah free zones with bonded-zone flags. Oman logistics, Sohar port, Salalah port, Duqm SEZAD, Khasab, UN/LOCODE, IATA codes, Royal Oman Police Customs, Oman Tax Authority, Oman free zones, Odoo 19 Community freight forwarding master data.',
    'description': 'Sultanate of Oman localisation pack for the ERP Heritage logistics suite. Preloads four master-data registers (sea ports, airports, customs offices, free zones) with the real Oman records an operator works with, ready to reference from freight jobs and customs work. Master data only, it extends eh_log_base and adds no operational workflow of its own.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': ['eh_log_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/eh_log_l10n_om_free_zone_data.xml',
        'data/eh_log_l10n_om_port_data.xml',
        'data/eh_log_l10n_om_airport_data.xml',
        'data/eh_log_l10n_om_customs_office_data.xml',
        'views/eh_log_l10n_om_views.xml',
        'views/eh_log_l10n_om_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
