# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
{
    'name': 'Track and Trace',
    'summary': 'Customer-facing shipment visibility for the ERP Heritage logistics suite, built on a single append-only event log that freight jobs, transport trips, last-mile deliveries, and waves all emit normalized events into, with a no-login public timeline page reached by a non-enumerable token, HMAC-SHA256 verified inbound carrier webhooks, and per-partner milestone notifications. Search terms: Odoo 19 track and trace, shipment tracking page, public parcel tracking, carrier webhook ingest, normalized event log, milestone notifications, freight forwarding visibility, transport trip tracking, last-mile delivery status, multi-company logistics tracking.',
    'description': 'Track and Trace adds a public shipment tracking page and a single normalized event log to the ERP Heritage logistics suite. A trackable mixin gives freight jobs, transport trips, last-mile deliveries, and waves a stable non-enumerable token and a public timeline URL, with every gated state transition emitting a normalized event. Inbound carrier webhooks are verified by HMAC-SHA256 signature before parsing, mapped from carrier vocabulary to a shared event-code set, and resolved back to the source record by tracking reference. Per-partner subscriptions queue milestone email notifications. Multi-company isolation, append-only enforcement, and a public-safe rendering path are built in.',
    'author': 'ERP Heritage',
    'website': 'https://www.erpheritage.com.au/',
    'license': 'LGPL-3',
    'category': 'Inventory/Delivery',
    'version': '19.0.1.0.0',
    'depends': [
        'eh_log_base',
        'eh_log_freight',
        'eh_log_transport',
        'eh_log_last_mile',
        'mail',
        'web',
    ],
    'data': [
        'security/eh_log_track_trace_security.xml',
        'security/eh_log_track_trace_isolation_rules.xml',
        'security/ir.model.access.csv',
        'data/eh_log_track_event_code_data.xml',
        'data/eh_log_track_email_template_data.xml',
        'data/eh_log_track_config_data.xml',
        'views/eh_log_track_event_code_views.xml',
        'views/eh_log_track_event_views.xml',
        'views/eh_log_track_event_kanban_calendar_pivot_graph_views.xml',
        'views/eh_log_track_subscription_views.xml',
        'views/eh_log_track_webhook_endpoint_views.xml',
        'views/eh_log_freight_job_views.xml',
        'views/eh_log_transport_trip_views.xml',
        'views/eh_log_last_mile_delivery_views.xml',
        'views/public_track_template.xml',
        'views/res_config_settings_views.xml',
        'views/eh_log_track_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
