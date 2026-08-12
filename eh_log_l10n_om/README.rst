Oman Logistics Localisation
===========================

**ERP Heritage Logistics Suite, eh_log_l10n_om**

An Oman master-data pack for the ERP Heritage logistics suite. It preloads the
country reference registers a freight forwarder or 3PL operator works with on day
one: sea ports, airports, customs offices, and free zones. It is master data
only. It extends eh_log_base and adds no operational workflow of its own.

+ **Version:** 19.0.1.0.0
+ **Licence:** LGPL-3
+ **Odoo:** 19.0 Community
+ **Author:** ERP Heritage

Overview
--------

eh_log_l10n_om seeds four reference registers as standalone master-data models,
each with its own list and form view and a menu under the logistics master-data
section. The records are the real Oman ports, airports, customs houses, and free
zones, ready to reference from elsewhere in the suite. The pack ships no
adapters, no declarations, and no customs messaging. It is reference data plus
the screens to browse and maintain it.

What it ships
-------------

**Five sea ports**
  An ``eh.log.l10n.om.port`` register seeded with five Oman sea ports, each
  carrying a UN/LOCODE and terminal flags (container, bulk, petrochemical):
  Sohar (``OMSOH``), Salalah (``OMSLL``), Sultan Qaboos Port in Muscat
  (``OMMCT``), Port of Duqm (``OMDUQ``), and Khasab (``OMKHS``). Each record also
  records the operating entity. UN/LOCODE is unique per record.

**Five airports**
  An ``eh.log.l10n.om.airport`` register seeded with five Oman airports, each
  carrying an IATA code, an optional ICAO code, and a cargo-capable flag: Muscat
  International (``MCT`` / ``OOMS``), Salalah (``SLL`` / ``OOSA``), Khasab
  (``KHS`` / ``OOKB``), Duqm (``DQM`` / ``OODQ``), and Sohar (``OHS`` /
  ``OOSH``). IATA code is unique per record.

**Six customs offices**
  An ``eh.log.l10n.om.customs.office`` register seeded with six records across
  four office kinds (customs authority, port customs house, airport customs
  house, tax authority): the Royal Oman Police Customs Department, the Oman Tax
  Authority, the Sohar, Salalah, and Duqm port customs houses, and the Muscat
  airport customs house. The port and airport houses are linked to the Royal Oman
  Police Customs Department as their parent authority. The office code is unique
  per record.

**Four free zones**
  An ``eh.log.l10n.om.free.zone`` register seeded with four Oman free zones, each
  with a bonded-zone flag and the regulating authority: Sohar Free Zone
  (``SFZ``), Salalah Free Zone (``SLFZ``), the Special Economic Zone Authority of
  Duqm (``SEZAD``), and Al Mazunah Free Zone (``MZN``). The free-zone code is
  unique per record.

**Views and menus**
  A list and a form view for each of the four registers, and a top-level "Oman"
  menu under the logistics master-data section with four child entries (Free
  Zones, Ports, Airports, Customs Offices). The menus are gated to the logistics
  manager group.

**Access control**
  Read access for the logistics user group and full create, write, and unlink
  access for the logistics manager group, on all four models. Groups are
  inherited from eh_log_base.

What this module does not do
----------------------------

+ No customs adapter and no regulator messaging. There is no Bayan adapter, no
  declaration submit, status, or health-check message, and no message types of
  any kind. The pack is master data only.
+ No declaration types and no HS or tariff overlay. It seeds no customs
  declaration types and no HS code records, and it does not extend any HS or
  tariff model.
+ No VAT-on-import handling, no currency master, no trade-licence master, and no
  public-holiday calendar.
+ No bilingual document templates and no PDF reports.
+ No dashboard, KPI tiles, disputes, track-and-trace, or EDI dispatch.
+ No search views, kanban views, scheduled jobs (crons), XSD files, or
  onboarding documents directory.
+ No demo data and no tests directory in this module.
+ No brand-attribution PDF footer and no integrity check. The module renders no
  PDFs and contains no such logic.
+ It depends only on ``eh_log_base``. It does not depend on a freight or customs
  engine.

Installation
------------

1. Drop this module folder into your Odoo addons path.
2. Refresh the module list, then install ``eh_log_l10n_om``. Its dependency
   installs automatically:

+ ``eh_log_base``

Configuration
-------------

After install, grant the ``eh_log_base.group_eh_log_user`` group to operators who
should read the registers and the ``eh_log_base.group_eh_log_manager`` group to
users who should maintain them. The "Oman" master-data menu is visible to the
manager group. The seeded records are available immediately with no further
setup.

Dependencies
------------

+ ``eh_log_base``

Licence
-------

Published under the LGPL-3 licence.
