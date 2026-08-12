Disputes and Variations
=======================

**ERP Heritage Logistics Suite — eh_log_disputes_variations**

Cargo claims, contested charges, and post-confirmation scope changes. Polymorphic against any operational record. SLA cron with overdue alerts, settlement letter, variation order, and dispute notice PDFs.

+ **Version:** 19.0.1.0.0
+ **Licence:** LGPL-3
+ **Odoo:** 19.0 Community
+ **Author:** ERP Heritage (https://www.erpheritage.com.au/)

Overview
--------

Commercial dispute resolution and post-confirmation scope change management. Disputes and variations share infrastructure (polymorphic source link, SLA timer, financial impact) so they live in one module.

Installation
------------

1. Drop this module folder into your Odoo addons-path.
2. Update the module list:

   .. code-block:: bash

      odoo-bin -d <database> -u base --stop-after-init

3. Install the module:

   .. code-block:: bash

      odoo-bin -d <database> -i eh_log_disputes_variations --stop-after-init

Dependencies are installed automatically:

+ ``eh_log_base``
+ ``eh_log_quotation``
+ ``eh_log_freight``
+ ``sale_management``
+ ``mail``

To install **with demo data** (sample partners, sale orders, freight jobs, etc.) add ``--with-demo`` to a fresh database:

   .. code-block:: bash

      odoo-bin -d <database> -i eh_log_disputes_variations --with-demo --stop-after-init

Configuration
-------------

After install:

1. Go to **Settings > Users & Companies > Groups** and grant the ``eh_log_base.group_eh_log_user`` group to operators, ``group_eh_log_manager`` to managers, and ``group_eh_log_auditor`` to read-only audit users.
2. Open **Logistics > Configuration > Adapters** and create the regulator / carrier / EDI adapter profiles you need; each adapter ships with sandbox defaults so you can validate the wire-up before going live.
3. Open **Logistics > Configuration > Master Data** and review the seeded charge codes, document types, and country-specific records (ports, free zones, customs offices).

Capabilities
------------

**Polymorphic source link**
  8 trackable / billable models (sale order, freight job, transport trip, last-mile delivery, warehouse receipt / pick, ship DA, container) supported.

**Eight dispute categories**
  Cargo damage, loss, short shipment, pricing, demurrage, documentation, customs penalty, other. Each carries default SLA days and survey-required flag.

**Dispute state machine**
  opened → investigating → offered → accepted → settled → closed (or rejected → escalated → written_off).

**Variation state machine**
  draft → submitted → approved → applied → closed. Apply step pushes new lines to the source sale order.

**Append-only event log**
  [EHL-DSP-009/010/011] block direct create / locked-field write / unlink. Every state transition logs.

**Financial fields with guards**
  Claimed / offered / settled with [EHL-DSP-005] blocking offer-exceeds-claim. Computed exposure for the dashboard tile.

**SLA breach cron**
  Daily cron walks open disputes with sla_target_date in the past; posts a mail.activity warning to the responsible user.

**Variation atomic apply**
  Approved variation pushes new SO lines tagged with the variation reference. Stored in applied_line_ids for future reversal traceability.

**Dispute notice PDF**
  Reference, customer, category, subject, source, state, SLA target. Description + financials + event log table.

**Settlement letter PDF**
  In-full-and-final-satisfaction language with signature panels for agent + customer.

**Variation order PDF**
  Reference, customer, source, sale order, state, variation lines (qty × price × subtotal), net variation. Acknowledgement panels.

**Mass settle / mass write-off**
  Operator picks N disputes, settles or writes them all off in one transaction. Skipped rows reported.

Day-one workflow
----------------

1. **Configure the master data.** Currencies, partners, charge codes, and the country pack: do this once at install.

2. **Operate the lifecycle.** State transitions through the buttons; mass actions from the list view; kanban for visual work.

3. **Audit and report.** Every action posts to the chatter, every state transition logs an event, every PDF carries the integrity-checked footer.

4. **Bill and reconcile.** Cost / revenue lines flow through the standard sale order to invoice path; multi-currency and multi-company respected.

Integrations
------------

**Sale order is the single source of truth**
  Customer, currency, incoterm, and lane all derive from the sale order. The module reads, never duplicates.

**Track and trace**
  Inherits the trackable mixin; every state transition emits a normalised tracking event on the public timeline.

**Disputes & variations**
  Polymorphic source link. Cargo claims, contested charges, and scope changes attach directly through the stat buttons on the form.

**ERP Heritage Dashboard**
  Live KPI tiles + cross-suite pivots. Drill from a tile to the underlying records in two clicks.

**EDI Hub**
  Outbound IFTMIN / IFTSTA dispatch through the EDI queue with multi-transport support; inbound webhook ingress with HMAC-SHA256 verification.

**Odoo Accounting**
  Standard sale order to invoice path. Multi-currency conversion at company rate; multi-company respected; VAT on import handled by the country pack.

Troubleshooting
---------------

**The module does not appear in the Apps list.**
  Make sure the module folder is in your addons-path. Run ``odoo-bin -u base`` once to refresh the module list, then remove the **Apps** filter in the UI to see community modules.

**Permission denied opening a record.**
  Confirm the user has the ``eh_log_base.group_eh_log_user`` group and that the record's ``company_id`` is in the user's ``allowed_company_ids``. The suite enforces multi-company isolation through global ``ir.rule`` records.

**Adapter calls fail with ``[EHL-CFG-002] Missing credential``.**
  Set the credential via ``ir.config_parameter`` or the OS environment variable named on the credential helper page; never store secrets in source. The helper looks up env vars first, then encrypted parameters, then the explicit default.

**Brand attribution check fails on PDF render.**
  The suite ships with a SHA-256 verifier on the brand-attribution chunks. Tampering or whitelabel without an official key will fail the check; the suite refuses to render. Contact ERP Heritage for whitelabel licensing.

FAQ
---

**Does this run on Odoo 19 Community?**

  Yes. The suite is built and tested on Odoo 19 Community. No Enterprise modules are required.

**Will it conflict with another addon?**

  Inheritance ordering is documented and the model names are eh.log.* throughout. A third-party addon that does not use those names is unaffected.

**Are tests included?**

  Yes. Unit tests, integration (e2e) tests, country matrix tests, and load tests are all included.

**How do I rebrand?**

  The publisher offers a paid whitelabel licence. Without the whitelabel files the integrity check fails and the suite refuses to operate.

Support
-------

Open source under LGPL-3 (with the brand-attribution footer constraint). For commercial whitelabel licensing, implementation services, or tier-1 support contact https://www.erpheritage.com.au/.

Issues raised on the public repository are taken seriously and fixes ship on the public branch.

Licence
-------

This module is published under the **LGPL-3** licence with one publisher requirement: the brand-attribution footer ``Made with love from Melbourne, Australia by ERP Heritage`` must remain intact and renders on every PDF. Tampering with the brand line fails the SHA-256 integrity check and the suite refuses to operate. Whitelabel licences are available from the publisher.
