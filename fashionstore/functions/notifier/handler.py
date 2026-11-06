"""notifier: SNS checkout-status -> notification_log -> SES email.

Effectively once per checkout: duplicates and concurrent deliveries are
suppressed by notification_log (UNIQUE checkout_id plus a lease). A crash
between SES accepting the email and the SENT update produces one duplicate
email on retry, which shows up as attempts > 1.

Failures raise, so Lambda's async retries (2) apply, and after that the event
goes to the notifier-failures SQS queue (the on-failure destination).
"""
from __future__ import annotations

import html
import json
import logging
import os
import pathlib
from string import Template

import boto3

from fashionstore_common import db
from repository import CLAIMED, IN_FLIGHT, SENT, NotificationRepository

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

TEMPLATES = pathlib.Path(__file__).resolve().parent / "templates"
REASON_TEXT = {
    "OUT_OF_STOCK": "an item sold out before we could reserve it",
    "PAYMENT_DECLINED": "the payment was declined",
    "UNKNOWN_SKU": "an item is no longer available",
}
SUBJECTS = {
    "CONFIRMED": "Your FashionStore order #{order_id} is confirmed",
    "REJECTED": "We couldn't complete your FashionStore order",
}


class InFlight(RuntimeError):
    """Another invocation is sending this email right now. Retry later."""


def render(event: dict) -> tuple[str, str]:
    status = event["status"]
    values = {
        "order_id": html.escape(str(event["order_id"])),
        "checkout_id": html.escape(event["checkout_id"]),
        "total": f"{int(event['total_cents']) / 100:.2f}",
        "reason_text": html.escape(REASON_TEXT.get(event.get("reason") or "", "the order could not be processed")),
    }
    body = Template((TEMPLATES / f"{status.lower()}.html").read_text()).substitute(values)
    return SUBJECTS[status].format(order_id=event["order_id"]), body


class SesSender:
    def __init__(self, sender: str, configuration_set: str | None = None, client=None):
        self.sender = sender
        self.configuration_set = configuration_set
        self.client = client or boto3.client("sesv2")

    def send(self, to: str, subject: str, body_html: str) -> str:
        kwargs = {
            "FromEmailAddress": self.sender,
            "Destination": {"ToAddresses": [to]},
            "Content": {"Simple": {"Subject": {"Data": subject, "Charset": "UTF-8"},
                                   "Body": {"Html": {"Data": body_html, "Charset": "UTF-8"}}}},
        }
        if self.configuration_set:
            kwargs["ConfigurationSetName"] = self.configuration_set
        return self.client.send_email(**kwargs)["MessageId"]


class Notifier:
    def __init__(self, repo: NotificationRepository, sender):
        self.repo = repo
        self.sender = sender

    def notify(self, event: dict) -> str:
        if event.get("schema_version") != 1 or event.get("status") not in SUBJECTS:
            raise ValueError(f"unsupported checkout-status event: {event!r}")
        checkout_id, email = event["checkout_id"], event["email"]

        state = self.repo.claim(checkout_id, email, event["status"])
        if state == SENT:
            return "SKIPPED_DUPLICATE"
        if state == IN_FLIGHT:
            raise InFlight(checkout_id)
        assert state == CLAIMED

        subject, body = render(event)
        try:
            message_id = self.sender.send(email, subject, body)
        except Exception as exc:
            self.repo.mark_failed(checkout_id, f"{type(exc).__name__}: {exc}")
            raise
        self.repo.mark_sent(checkout_id, message_id)
        return "SENT"


def build_notifier() -> Notifier:
    return Notifier(
        NotificationRepository(db.get_connection(), int(os.environ.get("LEASE_SECONDS", "120"))),
        SesSender(os.environ["SENDER_EMAIL"], os.environ.get("SES_CONFIGURATION_SET") or None),
    )


def handle(event: dict, notifier: Notifier) -> list[str]:
    results = []
    for record in event.get("Records", []):
        msg = json.loads(record["Sns"]["Message"])
        result = notifier.notify(msg)
        log.info(json.dumps({"event": "notification", "checkout_id": msg.get("checkout_id"), "result": result}))
        results.append(result)
    return results


def lambda_handler(event, context):
    return {"results": handle(event, build_notifier())}
