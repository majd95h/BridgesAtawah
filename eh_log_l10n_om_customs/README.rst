Oman Customs (Bayan) Adapter
============================

**ERP Heritage Logistics Suite, eh_log_l10n_om_customs**

An Oman customs adapter for the ERP Heritage logistics suite. It teaches the
shared customs engine how to exchange declaration messages with the Royal Oman
Police Customs Bayan single window, and it seeds the Oman declaration types and
a starter HS tariff overlay. It adds no views or menus of its own; declarations
are created and operated in the customs engine (eh_log_customs) that this pack
extends.

+ **Version:** 19.0.1.0.0
+ **Licence:** LGPL-3
+ **Odoo:** 19.0 Community
+ **Author:** ERP Heritage

Overview
--------

eh_log_l10n_om_customs ships the Bayan JSON adapter for Oman. It builds and
parses messages against the documented Bayan field shape. The adapter declares a
``bayan`` provider code on API version ``1.0`` and registers itself with the
shared adapter registry on import. The module adds no Odoo models or fields of
its own; its security file is an empty access table because it ships no new
models. Everything operational (transport, audit, resilience) comes from the
shared engine that this pack extends.

What it ships
-------------

**Bayan adapter**
  A concrete adapter for the Royal Oman Police Customs Bayan system with three
  message types: declaration submit, declaration status, and health check. Any
  other message type is refused with a clear typed error. A regulator response
  is parsed into a structured result, and a malformed submit response raises a
  typed validation error with the parse detail preserved for support.

**Seven Oman declaration types**
  Seven country scoped customs declaration types seeded into the engine for
  Oman, ready to use on a declaration without hand keying master data first:
  Import, Export, Transit, Re-export, Temporary Admission, GCC Inter-state
  Movement, and Import to Free Zone or SEZ. The Import type is flagged as
  requiring deferment.

**Oman HS and tariff overlay**
  A starter set of six Oman HS code records carrying duty and VAT defaults. VAT
  is seeded at the five percent Oman baseline, with the higher duty rates on the
  categories that carry excise (for example tobacco and sweetened carbonated
  beverages) and a zero rate on medicaments. It is a starting point that
  operators extend with the full national tariff.

**Mock mode default profile**
  A seeded Bayan adapter profile that defaults to the mock environment, so a
  fresh install replays bundled fixtures deterministically and never calls a
  live regulator endpoint by accident. The profile also seeds the engine
  resilience settings (request timeout, retry attempts, circuit breaker
  threshold and cooldown).

**Per company credentials**
  The credential lookup is company scoped, so one Odoo install can dispatch to
  two companies' Bayan accounts. Secrets resolve through the engine precedence
  chain: environment variable first (``EH_LOG_BAYAN_API_KEY`` or
  ``BAYAN_API_KEY``), then an encrypted config parameter (``bayan.api_key``),
  then an explicit default. The resolved value is sent as a bearer token and is
  never logged.

**Resilience and audit (from the engine)**
  HTTPS transport, the circuit breaker, retry with backoff, and the append only
  adapter message audit log are inherited from the shared logistics
  orchestrator in eh_log_base. Every request and response is recorded, with
  sensitive headers redacted.

What this module does not do
----------------------------

+ No amendment or cancellation message. Only declaration submit, declaration
  status, and health check are implemented.
+ No status polling cron. There is no scheduled job in this module; status is
  queried on demand through the status message.
+ No views, menus, search, kanban, or dashboard records of its own.
  Declarations are created, filtered, and grouped in the customs engine
  (eh_log_customs); this pack only adds the Bayan adapter and master data.
+ No new Odoo models or fields. The security access table is empty because the
  module defines no models.
+ No XSD files and no schema validation. Messages are built and parsed against
  the documented Bayan JSON field shape.
+ No Khazaen inland-bonded register, no VAT-on-import posting logic, and no
  declaration-type pre-mapping beyond the seeded type records.
+ No reports, no PDF footer, no trade-licence master, no HS-code model
  extension, no holiday calendar, no bilingual document templates, and no EDI
  hub messages.
+ No onboarding documents directory. There is no docs folder in this module.
+ No demo data. The manifest demo list is empty.

Installation
------------

1. Drop this module folder into your Odoo addons path.
2. Refresh the module list, then install ``eh_log_l10n_om_customs``. Its
   dependencies install automatically:

+ ``eh_log_base``
+ ``eh_log_customs``
+ ``eh_log_l10n_om``

Because the manifest sets ``auto_install``, the pack also installs by itself
once the customs engine and the Oman localisation pack are both present.

Configuration
-------------

1. Grant the ``eh_log_base.group_eh_log_user`` group to operators,
   ``group_eh_log_manager`` to managers, and ``group_eh_log_auditor`` to read
   only audit users.
2. The seeded Bayan profile starts in the mock environment. To go live, set the
   Bayan credential through an environment variable or an encrypted config
   parameter, then move the profile environment to sandbox and then to
   production.

Note on the endpoint. The seeded profile carries a placeholder Bayan host as the
protocol base string, used only to build request paths in non mock environments.
It is not a callable endpoint and the mock profile never dials out.

Troubleshooting
---------------

**Adapter calls fail with ``[EHL-CFG-002] Missing credential``.**
  Set the credential via an environment variable or an ``ir.config_parameter``
  entry. The helper looks up environment variables first, then encrypted
  parameters, then the explicit default. Never store secrets in source.

**Permission denied opening a record.**
  Confirm the user holds the ``eh_log_base.group_eh_log_user`` group and that
  the record's ``company_id`` is in the user's allowed companies. The suite
  enforces multi company isolation through global ``ir.rule`` records.

FAQ
---

**Does this run on Odoo 19 Community?**

  Yes. The suite is built and tested on Odoo 19 Community. No Enterprise modules
  are required.

**Are tests included?**

  Yes. A fixture backed test suite covers the adapter registration, the seeded
  mock profile, well formed submit serialisation, structured parsing of the
  success and rejection fixtures, and a mock mode round trip that writes an
  adapter message.

Licence
-------

Published under the LGPL-3 licence.
