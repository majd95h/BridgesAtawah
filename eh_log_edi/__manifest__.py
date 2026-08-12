# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'EDI Hub',
    'summary': 'An EDIFACT message hub for freight forwarders and 3PL operators that turns Odoo freight jobs into wire-ready EDI and ingests carrier status reports back onto the tracking log, with retry, dead-letter, and audit built in. Covers EDI for logistics, UN/EDIFACT IFTMIN forwarding instruction, IFTSTA multimodal status report, per-partner EDI mapping, SFTP SMTP HTTP and file-drop transport, inbound and outbound message queues, dead-letter handling, multi-company EDI, Odoo 19 Community freight integration, electronic data interchange for transport and 3PL.',
    'description': 'Generic EDIFACT message hub for the ERP Heritage logistics suite. Ships two end-to-end translators (IFTMIN outbound from freight jobs, IFTSTA inbound to the tracking log), a per-partner configuration registry, multi-transport dispatch (SFTP, SMTP, HTTP, file drop), and inbound plus outbound queues with retry budgets, dead-letter, and operator resume. Built for Odoo 19 Community.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': [
        'eh_log_base',
        'eh_log_freight',
        'eh_log_track_trace',
        'mail',
    ],
    'data': [
        'security/eh_log_edi_security.xml',
        'security/eh_log_edi_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_edi_message_type_data.xml',
        'data/eh_log_edi_sequences.xml',
        'data/eh_log_edi_cron.xml',
        'views/eh_log_edi_message_type_views.xml',
        'views/eh_log_edi_transport_views.xml',
        'views/eh_log_edi_partner_views.xml',
        'views/eh_log_edi_outbound_views.xml',
        'views/eh_log_edi_inbound_views.xml',
        'views/eh_log_edi_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_edi_search_views.xml',
        'views/eh_log_freight_job_views.xml',
        'wizards/eh_log_edi_mass_action_views.xml',
        'views/res_config_settings_views.xml',
        'views/eh_log_edi_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
