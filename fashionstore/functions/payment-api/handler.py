"""payment-api: simulated payment gateway (no VPC).

Deterministic and retry-safe: the same checkout_id and amount always produce
the same decision and the same payment_ref. Decline rules, for demos and tests:
  * amount_cents > MAX_AMOUNT_CENTS (default 500000)  -> LIMIT_EXCEEDED
  * the email local part contains "+decline"           -> CARD_DECLINED
  * sha256(checkout_id) bucket < DECLINE_PERCENT (default 0) -> CARD_DECLINED
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class BadRequest(ValueError):
    pass


def decide(checkout_id: str, amount_cents: int, email: str,
           max_amount_cents: int, decline_percent: int) -> dict:
    if not isinstance(checkout_id, str) or not UUID_RE.match(checkout_id):
        raise BadRequest("checkout_id must be a lowercase UUID")
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool) or amount_cents < 0:
        raise BadRequest("amount_cents must be a non-negative integer")
    if not isinstance(email, str) or "@" not in email:
        raise BadRequest("email is invalid")

    digest = hashlib.sha256(checkout_id.encode()).hexdigest()
    ref = f"pay_{digest[:20]}"
    reason = None
    if amount_cents > max_amount_cents:
        reason = "LIMIT_EXCEEDED"
    elif "+decline" in email.split("@", 1)[0].lower():
        reason = "CARD_DECLINED"
    elif int(digest[:8], 16) % 100 < decline_percent:
        reason = "CARD_DECLINED"
    return {"approved": reason is None, "payment_ref": ref, "reason": reason}


def lambda_handler(event, context):
    result = decide(
        event.get("checkout_id"),
        event.get("amount_cents"),
        event.get("email"),
        max_amount_cents=int(os.environ.get("MAX_AMOUNT_CENTS", "500000")),
        decline_percent=int(os.environ.get("DECLINE_PERCENT", "0")),
    )
    log.info(json.dumps({"event": "payment_decision", "checkout_id": event.get("checkout_id"), **result}))
    return result
