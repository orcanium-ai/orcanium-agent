"""Send Email Tool -- outbound SMTP email delivery.

Headless, transactional email to a recipient (e.g. a marketing agent
messaging clients). Deliberately independent of the messaging gateway: no live
channel/session is required, so it works from cron campaigns or CLI.

Reuses the same SMTP path as ``channel/platforms/email.py`` (EMAIL_ADDRESS /
EMAIL_PASSWORD / EMAIL_SMTP_HOST) but with an explicit subject and no
reply-threading, so it suits outbound sends rather than chat replies.
"""

import os
import smtplib
import ssl
import uuid
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from orcanium.app.tools.registry import registry, tool_error, tool_result

SEND_EMAIL_SCHEMA = {
    "name": "send_email",
    "description": (
        "Send an outbound email via SMTP to a recipient. "
        "Transactional, headless delivery to clients — no chat session or "
        "gateway needed. Use for notifications, reports, or marketing email. "
        "Requires email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD, "
        "EMAIL_SMTP_HOST)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address, e.g. jane@client.com.",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line.",
            },
            "body": {
                "type": "string",
                "description": "Plain-text email body.",
            },
            "attachments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of local file paths to attach.",
            },
        },
        "required": ["to", "subject", "body"],
    },
}


def _send_email(to: str, subject: str, body: str, attachments: list) -> str:
    """Send via SMTP. Returns the generated Message-ID. Raises on failure."""
    addr = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_host = os.environ["EMAIL_SMTP_HOST"]
    smtp_port = int(os.environ.get("EMAIL_SMTP_PORT") or "587")

    msg = MIMEMultipart()
    msg["From"] = addr
    msg["To"] = to
    msg["Subject"] = subject or "Orcanium Agent"
    msg["Date"] = formatdate(localtime=True)
    domain = addr.split("@")[-1] if "@" in addr else "localhost"
    msg["Message-ID"] = f"<orcanium-{uuid.uuid4().hex[:12]}@{domain}>"
    msg.attach(MIMEText(body or "", "plain", "utf-8"))

    for path in attachments:
        with open(path, "rb") as f:
            part = MIMEApplication(f.read())
            part["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(path)}"'
            )
            msg.attach(part)

    smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
    try:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(addr, password)
        smtp.send_message(msg)
    finally:
        try:
            smtp.quit()
        except Exception:
            smtp.close()
    return msg["Message-ID"]


def send_email_tool(args, **kw):
    to = (args.get("to") or "").strip()
    subject = (args.get("subject") or "").strip()
    body = (args.get("body") or "").strip()
    if not to:
        return tool_error("'to' is required.")

    if not (
        os.environ.get("EMAIL_ADDRESS")
        and os.environ.get("EMAIL_PASSWORD")
        and os.environ.get("EMAIL_SMTP_HOST")
    ):
        return tool_error(
            "Email not configured. Set EMAIL_ADDRESS, EMAIL_PASSWORD, and "
            "EMAIL_SMTP_HOST."
        )

    attachments = args.get("attachments") or []
    try:
        message_id = _send_email(to, subject, body, attachments)
    except FileNotFoundError as e:
        return tool_error(f"Attachment not found: {e}")
    except smtplib.SMTPAuthenticationError as e:
        return tool_error(f"SMTP auth failed: {e.smtp_code} {e.smtp_error}")
    except Exception as e:
        return tool_error(f"Email send failed: {e}")

    return tool_result(success=True, to=to, subject=subject, message_id=message_id)


def _check_send_email():
    return bool(
        os.environ.get("EMAIL_ADDRESS")
        and os.environ.get("EMAIL_PASSWORD")
        and os.environ.get("EMAIL_SMTP_HOST")
    )


registry.register(
    name="send_email",
    toolset="messaging",
    schema=SEND_EMAIL_SCHEMA,
    handler=send_email_tool,
    check_fn=_check_send_email,
    emoji="📧",
)
