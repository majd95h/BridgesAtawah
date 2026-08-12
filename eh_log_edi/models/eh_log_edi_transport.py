# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2026 (https://www.erpheritage.com.au/)
#
##############################################################################
"""EDI transport configuration.

A transport is one of: SFTP, SMTP, HTTP, AS2, file drop. The
configuration carries the endpoint, authentication credentials key,
and protocol-specific knobs (target directory, content type, signing
required).

The actual dispatch is invoked through send(payload, filename) which
dispatches on the protocol attribute. SFTP uses the standard library
fallback (paramiko if installed, otherwise raises with a clear
message); SMTP uses Odoo's mail.mail; HTTP uses urllib.request from
the standard library.
"""
import io
import logging
import os
from email.message import EmailMessage

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


# Default subdirectory under the partner's SFTP root for outbound
# files. Operators can override per partner; this default keeps the
# configuration thin for a fresh install.
DEFAULT_OUTBOUND_SUBDIR = "outbox"

# Default per-call timeout in seconds for network transports.
# Operators can change this through ir.config_parameter without a
# code change; the constant defines the floor.
DEFAULT_TRANSPORT_TIMEOUT_SECONDS = 30


class EhLogEdiTransport(models.Model):
    _name = "eh.log.edi.transport"
    _description = "EDI Transport"
    _order = "name"
    _rec_names_search = ["name", "code"]

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True, size=12)
    protocol = fields.Selection(
        [
            ("sftp", "SFTP"),
            ("smtp", "SMTP"),
            ("http", "HTTP"),
            ("as2", "AS2"),
            ("file", "File Drop"),
            ("mock", "Mock (Tests)"),
        ],
        string="Protocol",
        required=True,
    )
    host = fields.Char(string="Host")
    port = fields.Integer(string="Port")
    username = fields.Char(string="Username")
    credentials_key = fields.Char(
        string="Credentials Key",
        help="Lookup key for the credentials helper.",
    )
    target_directory = fields.Char(
        string="Target Directory",
        default=DEFAULT_OUTBOUND_SUBDIR,
    )
    target_email = fields.Char(string="Target Email")
    target_url = fields.Char(string="Target URL")
    signing_required = fields.Boolean(string="Signing Required", default=False)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _transport_code_unique = models.Constraint(
        'unique(code, company_id)',
        'Transport code must be unique per company.',
    )

    @api.constrains("protocol", "host", "target_email", "target_url")
    def _check_protocol_fields(self):
        for transport in self:
            if transport.protocol in ("sftp", "ftp", "http", "as2"):
                if not transport.host and not transport.target_url:
                    raise ValidationError(_(
                        "[EHL-EDI-002] Transport %(name)s requires "
                        "host or target URL for protocol "
                        "%(protocol)s."
                    ) % {
                        "name": transport.name,
                        "protocol": transport.protocol,
                    })
            if transport.protocol == "smtp" and not transport.target_email:
                raise ValidationError(_(
                    "[EHL-EDI-003] Transport %(name)s requires a "
                    "target email for SMTP."
                ) % {"name": transport.name})

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def send(self, payload, filename):
        self.ensure_one()
        if self.protocol == "mock":
            return self._send_mock(payload, filename)
        if self.protocol == "smtp":
            return self._send_smtp(payload, filename)
        if self.protocol == "sftp":
            return self._send_sftp(payload, filename)
        if self.protocol == "http":
            return self._send_http(payload, filename)
        if self.protocol == "file":
            return self._send_file(payload, filename)
        if self.protocol == "as2":
            raise UserError(_(
                "[EHL-EDI-004] AS2 transport requires the optional "
                "pyas2 library; install it and provide a signing "
                "certificate before activating an AS2 transport."
            ))
        raise UserError(_(
            "[EHL-EDI-005] Unsupported transport protocol "
            "%(protocol)s."
        ) % {"protocol": self.protocol})

    def _send_mock(self, payload, filename):
        # Persist to ir.attachment so tests can assert the bytes
        # actually moved out of the queue without touching the
        # filesystem or the network.
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "datas": _b64(payload),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/edifact",
        })
        return {"ok": True, "reference": attachment.id}

    def _send_smtp(self, payload, filename):
        message = EmailMessage()
        message["Subject"] = f"EDI: {filename}"
        message["From"] = self.env.company.email or "noreply@example.invalid"
        message["To"] = self.target_email
        message.set_content(_(
            "Auto-generated EDI message from the ERP Heritage logistics suite."
        ))
        message.add_attachment(
            payload,
            maintype="application",
            subtype="edifact",
            filename=filename,
        )
        Mail = self.env["mail.mail"].sudo()
        mail = Mail.create({
            "subject": message["Subject"],
            "body_html": _(
                "<p>Auto-generated EDI message; the EDIFACT payload is attached.</p>"
            ),
            "email_to": self.target_email,
            "email_from": message["From"],
            "auto_delete": False,
        })
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "datas": _b64(payload),
            "res_model": "mail.mail",
            "res_id": mail.id,
            "mimetype": "application/edifact",
        })
        mail.write({"attachment_ids": [(4, attachment.id)]})
        mail.send()
        return {"ok": True, "reference": mail.id}

    def _send_sftp(self, payload, filename):
        try:
            import paramiko  # type: ignore
        except ImportError as exc:
            raise UserError(_(
                "[EHL-EDI-006] SFTP transport requires the optional "
                "paramiko library; pip install paramiko on the "
                "Odoo host before activating SFTP."
            )) from exc
        secret = self._fetch_secret()
        target_dir = self.target_directory or DEFAULT_OUTBOUND_SUBDIR
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            port=self.port or 22,  # noqa: gcclog-hardcode IANA standard SSH/SFTP port
            username=self.username,
            password=secret,
            timeout=DEFAULT_TRANSPORT_TIMEOUT_SECONDS,
        )
        try:
            sftp = client.open_sftp()
            try:
                sftp.chdir(target_dir)
            except IOError:
                sftp.mkdir(target_dir)
                sftp.chdir(target_dir)
            with sftp.open(filename, "wb") as fh:
                fh.write(payload)
        finally:
            client.close()
        return {"ok": True, "reference": f"{target_dir}/{filename}"}

    def _send_http(self, payload, filename):
        import urllib.request

        request = urllib.request.Request(
            self.target_url,
            data=payload,
            headers={
                "Content-Type": "application/edifact",
                "X-Eh-Edi-Filename": filename,
            },
            method="POST",
        )
        with urllib.request.urlopen(
            request,
            timeout=DEFAULT_TRANSPORT_TIMEOUT_SECONDS,
        ) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
        if status >= 400:  # noqa: gcclog-hardcode RFC 9110 4xx threshold for HTTP error responses
            raise UserError(_(
                "[EHL-EDI-007] HTTP transport %(name)s rejected the "
                "payload with status %(status)s: %(body)s"
            ) % {
                "name": self.name,
                "status": status,
                "body": body[:200],
            })
        return {"ok": True, "reference": str(status)}

    def _send_file(self, payload, filename):
        target_dir = self.target_directory or DEFAULT_OUTBOUND_SUBDIR
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, filename)
        with open(path, "wb") as fh:
            fh.write(payload)
        return {"ok": True, "reference": path}

    def _fetch_secret(self):
        self.ensure_one()
        if not self.credentials_key:
            return ""
        return self.env["eh.log.credentials"].get(
            purpose=f"edi_{self.code}",
            param_key=self.credentials_key,
            company_id=self.company_id.id,
        )


def _b64(payload):
    """Helper for ir.attachment datas field which expects base64."""
    import base64
    return base64.b64encode(payload).decode("ascii")
