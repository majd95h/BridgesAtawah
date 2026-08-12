# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""Cold chain monitoring run.

One per (freight job, profile) attached to a freight job that requires
temperature monitoring. Aggregates readings, deviations, and produces
the compliance certificate.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.eh_log_base.exceptions import JobStateConflictError

_logger = logging.getLogger(__name__)


RUN_STATES = [
    ("draft", "Draft"),
    ("active", "Active"),
    ("completed", "Completed"),
    ("breached", "Breached (Cargo Impacting)"),
    ("cancelled", "Cancelled"),
]

ALLOWED_RUN_TRANSITIONS = {
    "draft": {"active", "cancelled"},
    "active": {"completed", "breached", "cancelled"},
    "completed": set(),
    "breached": set(),
    "cancelled": set(),
}


class EhLogColdChainRun(models.Model):
    _name = "eh.log.cold.chain.run"
    _description = "Cold Chain Monitoring Run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _rec_names_search = ["name"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )

    state = fields.Selection(
        selection=RUN_STATES,
        string="State",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    company_ids = fields.Many2many(
        "res.company",
        "eh_log_cold_chain_run_company_rel",
        "run_id",
        "company_id",
        string="Companies",
        compute="_compute_company_ids",
        store=True,
        index=True,
        precompute=True,
    )

    # ----- Linkage -----

    freight_job_id = fields.Many2one(
        "eh.log.freight.job",
        string="Freight Job",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    profile_id = fields.Many2one(
        "eh.log.cold.chain.profile",
        string="Profile",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )

    profile_temperature_min = fields.Float(
        related="profile_id.temperature_min",
        store=True,
        readonly=True,
    )

    profile_temperature_max = fields.Float(
        related="profile_id.temperature_max",
        store=True,
        readonly=True,
    )

    # ----- Window -----

    started_at = fields.Datetime(
        string="Started",
        readonly=True,
        copy=False,
        tracking=True,
    )

    completed_at = fields.Datetime(
        string="Completed",
        readonly=True,
        copy=False,
        tracking=True,
    )

    # ----- Lines -----

    reading_ids = fields.One2many(
        "eh.log.cold.chain.reading",
        "run_id",
        string="Readings",
    )

    reading_count = fields.Integer(
        string="Readings",
        compute="_compute_reading_count",
        store=True,
    )

    deviation_ids = fields.One2many(
        "eh.log.cold.chain.deviation",
        "run_id",
        string="Deviations",
    )

    deviation_count = fields.Integer(
        string="Deviations",
        compute="_compute_deviation_count",
        store=True,
    )

    open_deviation_count = fields.Integer(
        string="Open Deviations",
        compute="_compute_deviation_count",
        store=True,
    )

    # ----- Aggregates -----

    min_temperature = fields.Float(
        string="Min Recorded (degC)",
        compute="_compute_aggregates",
        store=True,
    )

    max_temperature = fields.Float(
        string="Max Recorded (degC)",
        compute="_compute_aggregates",
        store=True,
    )

    avg_temperature = fields.Float(
        string="Avg Recorded (degC)",
        compute="_compute_aggregates",
        store=True,
    )

    is_compliant = fields.Boolean(
        string="Compliant",
        compute="_compute_aggregates",
        store=True,
        help="True when no cargo-impacting deviation has been recorded "
             "and at least one reading has been ingested. Drives the "
             "compliance certificate verdict.",
    )

    notes = fields.Text(string="Notes")

    # ----- Computes -----

    @api.depends("company_id")
    def _compute_company_ids(self):
        for run in self:
            run.company_ids = run.company_id

    @api.depends("reading_ids")
    def _compute_reading_count(self):
        for run in self:
            run.reading_count = len(run.reading_ids)

    @api.depends("deviation_ids", "deviation_ids.state")
    def _compute_deviation_count(self):
        for run in self:
            run.deviation_count = len(run.deviation_ids)
            run.open_deviation_count = len(run.deviation_ids.filtered(
                lambda d: d.state in ("open", "acknowledged")
            ))

    @api.depends(
        "reading_ids", "reading_ids.temperature",
        "deviation_ids", "deviation_ids.cargo_impacting",
        "deviation_ids.state",
    )
    def _compute_aggregates(self):
        for run in self:
            temps = run.reading_ids.mapped("temperature")
            if temps:
                run.min_temperature = min(temps)
                run.max_temperature = max(temps)
                run.avg_temperature = sum(temps) / len(temps)
            else:
                run.min_temperature = 0.0
                run.max_temperature = 0.0
                run.avg_temperature = 0.0
            cargo_impacting = run.deviation_ids.filtered(
                lambda d: d.cargo_impacting and d.state != "voided"
            )
            run.is_compliant = bool(temps) and not cargo_impacting

    # ----- Lifecycle -----

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "eh.log.cold.chain.run"
                ) or _("New")
        return super().create(vals_list)

    def _transition_state(self, target_state: str):
        for run in self:
            current = run.state
            allowed = ALLOWED_RUN_TRANSITIONS.get(current, set())
            if target_state not in allowed:
                raise JobStateConflictError(
                    122,
                    _(
                        "Cold chain run %(name)s cannot move from "
                        "%(current)s to %(target)s. Allowed transitions "
                        "from %(current)s: %(allowed)s."
                    ) % {
                        "name": run.name,
                        "current": current,
                        "target": target_state,
                        "allowed": ", ".join(sorted(allowed)) or _("(none)"),
                    },
                )
            run.with_context(eh_log_cold_chain_internal_state_write=True).write({
                "state": target_state,
            })
            self.env["eh.log.event"].log(
                category="state_transition",
                summary=_("Cold chain run %(name)s moved to %(state)s.") % {
                    "name": run.name, "state": target_state,
                },
                related_model="eh.log.cold.chain.run",
                related_record_id=run.id,
                related_record_display=run.name,
                context={"from_state": current, "to_state": target_state},
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("eh_log_cold_chain_internal_state_write"):
            raise UserError(_(
                "[EHL-COLD-CHAIN-001] State changes on a cold chain run "
                "must go through the action buttons. Direct writes are "
                "rejected."
            ))
        return super().write(vals)

    # ----- Actions -----

    def action_activate(self):
        self._transition_state("active")
        for run in self:
            if not run.started_at:
                run.started_at = fields.Datetime.now()
        return True

    def action_complete(self):
        cargo_impacting = self.deviation_ids.filtered(
            lambda d: d.cargo_impacting and d.state != "voided"
        )
        if cargo_impacting:
            # Auto-route to breached if any cargo-impacting deviation is open.
            self._transition_state("breached")
        else:
            self._transition_state("completed")
        for run in self:
            run.completed_at = fields.Datetime.now()
        return True

    def action_cancel(self):
        self._transition_state("cancelled")
        return True

    def action_view_readings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Readings"),
            "res_model": "eh.log.cold.chain.reading",
            "view_mode": "list,form",
            "domain": [("run_id", "=", self.id)],
            "context": {"default_run_id": self.id},
        }

    def action_view_deviations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Deviations"),
            "res_model": "eh.log.cold.chain.deviation",
            "view_mode": "list,form",
            "domain": [("run_id", "=", self.id)],
            "context": {"default_run_id": self.id},
        }

    # ----- Bulk ingest -----

    def ingest_readings(self, samples: list) -> int:
        """Bulk-create readings from a list of (timestamp, temp, humidity) tuples.

        Returns the number of readings created. Triggers deviation
        re-detection at the end. Designed for adapter ingest paths
        (telematics, sensor-stream files) that need to write hundreds
        or thousands of readings in one call.
        """
        self.ensure_one()
        if self.state != "active":
            raise UserError(_(
                "[EHL-COLD-CHAIN-002] Cold chain run %(name)s is in "
                "state %(state)s. Readings can only be ingested while "
                "the run is active."
            ) % {"name": self.name, "state": self.state})
        Reading = self.env["eh.log.cold.chain.reading"].sudo()
        vals_list = []
        for sample in samples:
            if len(sample) == 2:
                ts, temperature = sample
                humidity = False
            elif len(sample) == 3:
                ts, temperature, humidity = sample
            else:
                continue
            vals_list.append({
                "run_id": self.id,
                "captured_at": ts,
                "temperature": temperature,
                "humidity": humidity,
                "source": "ingest",
            })
        readings = Reading.create(vals_list)
        # After ingest, re-evaluate deviations.
        self._detect_deviations()
        return len(readings)

    def _detect_deviations(self):
        """Scan readings for sustained excursions and create deviation rows.

        A deviation is opened when readings exceed the profile's min
        or max for a continuous duration of at least
        ``alert_window_minutes``. A deviation closes when readings
        return inside the threshold for ``excursion_grace_minutes``.
        Existing open deviations are extended by re-running this
        scan; closed deviations are not duplicated.
        """
        self.ensure_one()
        if not self.profile_id or not self.reading_ids:
            return
        # Pull readings ordered by timestamp.
        readings = self.reading_ids.sorted("captured_at")
        profile = self.profile_id
        Deviation = self.env["eh.log.cold.chain.deviation"].sudo()
        existing = Deviation.search([("run_id", "=", self.id)])
        # Walk readings, identify continuous breach segments.
        breach_start = None
        breach_kind = None  # 'low' or 'high'
        breach_min = None
        breach_max = None
        for reading in readings:
            is_low = reading.temperature < profile.temperature_min
            is_high = reading.temperature > profile.temperature_max
            in_breach = is_low or is_high
            kind = "low" if is_low else ("high" if is_high else None)
            if in_breach:
                if breach_start is None or kind != breach_kind:
                    if breach_start is not None:
                        self._record_breach(
                            breach_start, reading.captured_at,
                            breach_kind, breach_min, breach_max, existing,
                        )
                    breach_start = reading.captured_at
                    breach_kind = kind
                    breach_min = reading.temperature
                    breach_max = reading.temperature
                else:
                    breach_min = min(breach_min, reading.temperature)
                    breach_max = max(breach_max, reading.temperature)
            else:
                if breach_start is not None:
                    self._record_breach(
                        breach_start, reading.captured_at,
                        breach_kind, breach_min, breach_max, existing,
                    )
                    breach_start = None
                    breach_kind = None
        # Tail breach (still open at end of readings)
        if breach_start is not None:
            last_reading = readings[-1]
            self._record_breach(
                breach_start, last_reading.captured_at,
                breach_kind, breach_min, breach_max, existing,
            )

    def _record_breach(self, start, end, kind, low, high, existing):
        """Create a deviation if the breach exceeds the alert window."""
        self.ensure_one()
        duration_minutes = (end - start).total_seconds() / 60.0
        if duration_minutes < (self.profile_id.alert_window_minutes or 0):
            return
        # Skip if an open deviation already covers this window
        for dev in existing:
            if dev.state == "voided":
                continue
            if dev.started_at <= start <= (dev.ended_at or end) and dev.deviation_kind == kind:
                # Extend the existing deviation
                dev.sudo().write({
                    "ended_at": end,
                    "min_temperature": min(dev.min_temperature, low),
                    "max_temperature": max(dev.max_temperature, high),
                })
                return
        Deviation = self.env["eh.log.cold.chain.deviation"].sudo()
        Deviation.create({
            "run_id": self.id,
            "deviation_kind": kind,
            "started_at": start,
            "ended_at": end,
            "min_temperature": low,
            "max_temperature": high,
        })
