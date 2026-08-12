Ship Agency
===========

**ERP Heritage Logistics Suite — eh_log_ship_agency**

Vessel master with IMO checksum, port call lifecycle, Statement of Facts append-only event log, Disbursement Account with estimate, actual, variance, husbandry catalog, Notice of Readiness, SOF, and DA PDFs.

+ **Version:** 19.0.1.0.0
+ **Licence:** LGPL-3
+ **Odoo:** 19.0 Community
+ **Author:** ERP Heritage (https://www.erpheritage.com.au/)

Overview
--------

Where the freight forwarding spine handles cargo, this module handles the vessel side: an agent representing a shipowner at a port, attending the call, posting Notice of Readiness, logging every operational event onto a Statement of Facts, settling the Disbursement Account.

Installation
------------

1. Drop this module folder into your Odoo addons-path.
2. Update the module list:

   .. code-block:: bash

      odoo-bin -d <database> -u base --stop-after-init

3. Install the module:

   .. code-block:: bash

      odoo-bin -d <database> -i eh_log_ship_agency --stop-after-init

Dependencies are installed automatically:

+ ``eh_log_base``
+ ``eh_log_quotation``
+ ``eh_log_freight``
+ ``sale_management``
+ ``mail``

To install **with demo data** (sample partners, sale orders, freight jobs, etc.) add ``--with-demo`` to a fresh database:

   .. code-block:: bash

      odoo-bin -d <database> -i eh_log_ship_agency --with-demo --stop-after-init

Configuration
-------------

After install:

1. Go to **Settings > Users & Companies > Groups** and grant the ``eh_log_base.group_eh_log_user`` group to operators, ``group_eh_log_manager`` to managers, and ``group_eh_log_auditor`` to read-only audit users.
2. Open **Logistics > Configuration > Adapters** and create the regulator / carrier / EDI adapter profiles you need; each adapter ships with sandbox defaults so you can validate the wire-up before going live.
3. Open **Logistics > Configuration > Master Data** and review the seeded charge codes, document types, and country-specific records (ports, free zones, customs offices).

Capabilities
------------

**Vessel master with IMO checksum**
  IMO Resolution A.1078(28) checksum validated; MMSI 9-digit format; GT/NT/DWT; owner / operator partner split.

**Berth master + compatibility check**
  Depth, max LOA, terminal operator, customs status. Vessel-berth compatibility checked at assignment time.

**Port call lifecycle**
  expected → arrived → berthed → working → sailed → closed (or cancelled). NOR tendered only between arrived and berthed.

**Statement of Facts append-only**
  Timestamped chronology of operational events: pilot on board, tugs fast, first line ashore, gangway down, cargo operations commenced, weather suspension.

**Disbursement Account spine**
  Estimate (proforma) / Actual / Posted / Settled. Variance = actual - estimate; positive = over budget.

**Husbandry service catalogue**
  Eight seeded categories: crew change, ship spares, provisions, fresh water, garbage, slop reception, bunker, medical.

**NOR PDF**
  Notice of Readiness with vessel + voyage + port + arrival time; signature panel for master + agent + receiver / charterer.

**SOF PDF**
  Statement of facts with vessel particulars + event table (time + description + category + counts-against-laytime).

**DA PDF**
  Disbursement Account with estimate column + actual column + variance + signature lines for principal approval.

**Close-call DA-gated**
  Cannot close the port call while the DA is in draft / proforma / actual. The settled or posted state of the DA unlocks the close.

**Multi-currency DA**
  DA carried in the principal's currency; conversion to the company's currency at posting. Multi-currency lines supported.

**Comprehensive search**
  Filters: state, vessel, port, principal, ETA today / this week, NOR tendered. Group-by: state, vessel, port, principal.

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
