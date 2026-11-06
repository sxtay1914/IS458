"""Checkout processing: validation, idempotency and the outcome decision.

Flow for one SQS message (see contracts/events/checkout-request.schema.json):
  1. If an order already exists for checkout_id, re-publish its outcome if it
     was never published, then ack. This is the duplicate-message path.
  2. Price the items from the database (never from the message).
  3. Call payment-api. It is deterministic per checkout_id, so a retry gets
     the same answer.
  4. One transaction: insert the order (UNIQUE checkout_id), conditionally
     decrement each SKU, insert the items, and update the checkout row.
     Insufficient stock rolls back and records a REJECTED order instead.
  5. Publish to SNS, then mark outcome_published_at. If publishing fails, the
     exception makes SQS retry the message, and step 1 re-publishes it.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_ITEMS = 20
MAX_QTY = 20

CONFIRMED = "CONFIRMED"
REJECTED = "REJECTED"
OUT_OF_STOCK = "OUT_OF_STOCK"
PAYMENT_DECLINED = "PAYMENT_DECLINED"
UNKNOWN_SKU = "UNKNOWN_SKU"


class InvalidMessage(ValueError):
    """The message can never succeed. It is reported as a failure so it ends up in the DLQ."""


class RetryableConflict(RuntimeError):
    """A deadlock or lock timeout. The transaction was rolled back and is safe to retry."""


@dataclass(frozen=True)
class Item:
    sku: str
    qty: int


@dataclass(frozen=True)
class CheckoutRequest:
    checkout_id: str
    user_sub: str
    email: str
    items: tuple[Item, ...]


@dataclass
class Outcome:
    checkout_id: str
    status: str
    reason: str | None
    order_id: int
    user_sub: str
    email: str
    total_cents: int
    published: bool = False
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_event(self) -> dict:
        ts = self.occurred_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return {
            "schema_version": 1,
            "checkout_id": self.checkout_id,
            "status": self.status,
            "reason": self.reason,
            "order_id": int(self.order_id),
            "user_sub": self.user_sub,
            "email": self.email,
            "total_cents": int(self.total_cents),
            "occurred_at": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        }


@dataclass(frozen=True)
class PaymentResult:
    approved: bool
    payment_ref: str
    reason: str | None = None


def parse_request(msg: dict) -> CheckoutRequest:
    if not isinstance(msg, dict):
        raise InvalidMessage("message must be a JSON object")
    if msg.get("schema_version") != 1:
        raise InvalidMessage(f"unsupported schema_version {msg.get('schema_version')!r}")
    checkout_id = msg.get("checkout_id")
    if not isinstance(checkout_id, str) or not UUID_RE.match(checkout_id):
        raise InvalidMessage("checkout_id must be a lowercase UUID")
    user_sub = msg.get("user_sub")
    if not isinstance(user_sub, str) or not 0 < len(user_sub) <= 64:
        raise InvalidMessage("user_sub is required")
    email = msg.get("email")
    if not isinstance(email, str) or "@" not in email or len(email) > 254:
        raise InvalidMessage("email is invalid")
    raw_items = msg.get("items")
    if not isinstance(raw_items, list) or not 0 < len(raw_items) <= MAX_ITEMS:
        raise InvalidMessage(f"items must have 1..{MAX_ITEMS} entries")
    merged: dict[str, int] = {}
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise InvalidMessage("each item must be an object")
        sku, qty = raw.get("sku"), raw.get("qty")
        if not isinstance(sku, str) or not 0 < len(sku) <= 64:
            raise InvalidMessage("item sku is invalid")
        if not isinstance(qty, int) or isinstance(qty, bool) or not 1 <= qty <= MAX_QTY:
            raise InvalidMessage(f"item qty must be 1..{MAX_QTY}")
        merged[sku] = merged.get(sku, 0) + qty
    if any(q > MAX_QTY for q in merged.values()):
        raise InvalidMessage(f"total qty per sku must be <= {MAX_QTY}")
    # Sorted by SKU so every transaction locks inventory rows in the same order (no deadlock cycles).
    items = tuple(Item(sku, qty) for sku, qty in sorted(merged.items()))
    return CheckoutRequest(checkout_id, user_sub, email, items)


class CheckoutService:
    def __init__(self, repo, payment, publisher, max_attempts: int = 3, sleep=time.sleep):
        self.repo = repo
        self.payment = payment
        self.publisher = publisher
        self.max_attempts = max_attempts
        self.sleep = sleep

    def process(self, msg: dict) -> Outcome:
        req = parse_request(msg)

        existing = self.repo.find_order(req.checkout_id)
        if existing is not None:
            self._publish(existing)
            return existing

        prices = self.repo.get_prices([i.sku for i in req.items])
        missing = [i.sku for i in req.items if i.sku not in prices]
        total = sum(prices.get(i.sku, 0) * i.qty for i in req.items)

        if missing:
            outcome = self._with_retry(lambda: self.repo.record_rejection(req, total, UNKNOWN_SKU, None))
        else:
            payment = self.payment.authorize(req.checkout_id, total, req.email)
            if not payment.approved:
                outcome = self._with_retry(
                    lambda: self.repo.record_rejection(req, total, PAYMENT_DECLINED, payment.payment_ref))
            else:
                outcome = self._with_retry(
                    lambda: self.repo.place_order(req, prices, total, payment.payment_ref))

        self._publish(outcome)
        return outcome

    def _with_retry(self, fn):
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except RetryableConflict:
                if attempt == self.max_attempts:
                    raise
                self.sleep(0.05 * attempt)
        raise AssertionError("unreachable")

    def _publish(self, outcome: Outcome) -> None:
        if outcome.published:
            return
        self.publisher.publish(outcome.to_event())
        self.repo.mark_published(outcome.checkout_id)
        outcome.published = True
