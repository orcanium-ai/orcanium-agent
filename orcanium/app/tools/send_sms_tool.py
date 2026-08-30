"""Send SMS Tool -- outbound Twilio SMS delivery.

Headless, transactional text delivery to a phone number (e.g. a marketing
agent messaging clients). Deliberately independent of the messaging gateway:
no live channel/session is required, so it works from cron campaigns or CLI.

Reuses the same Twilio REST path as ``channel/platforms/sms.py`` (SID + auth
token + From number) but with no inbound/webhook machinery.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from orcanium.app.tools.registry import registry, tool_error, tool_result

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01/Accounts"

SEND_SMS_SCHEMA = {
    "name": "send_sms",
    "description": (
        "Send an outbound SMS via Twilio to a phone number. "
        "Transactional, headless delivery to clients — no chat session or "
        "gateway needed. Use for one-way texts (notifications, follow-ups, "
        "marketing blasts). Requires Twilio credentials (TWILIO_ACCOUNT_SID, "
        "TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient phone number in E.164 format, e.g. +15551234567.",
            },
            "body": {
                "type": "string",
                "description": "SMS text. Long messages are auto-concatenated by Twilio.",
            },
        },
        "required": ["to", "body"],
    },
}


def send_sms_tool(args, **kw):
    to = (args.get("to") or "").strip()
    body = (args.get("body") or "").strip()
    if not to or not body:
        return tool_error("Both 'to' and 'body' are required.")

    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
    if not sid or not token or not from_number:
        return tool_error(
            "Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_PHONE_NUMBER."
        )

    url = f"{TWILIO_API_BASE}/{sid}/Messages.json"
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    data = urllib.parse.urlencode(
        {"From": from_number, "To": to, "Body": body}
    ).encode()

    req = urllib.request.Request(
        url, data=data, headers={"Authorization": f"Basic {auth}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_json = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace") or str(e)
        return tool_error(f"Twilio {e.code}: {detail}")
    except Exception as e:
        return tool_error(f"SMS send failed: {e}")

    if not resp_json.get("sid"):
        return tool_error("Twilio did not return a message SID.")
    return tool_result(success=True, to=to, sid=resp_json["sid"])


def _check_send_sms():
    return bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and os.environ.get("TWILIO_PHONE_NUMBER")
    )


registry.register(
    name="send_sms",
    toolset="messaging",
    schema=SEND_SMS_SCHEMA,
    handler=send_sms_tool,
    check_fn=_check_send_sms,
    emoji="💬",
)
