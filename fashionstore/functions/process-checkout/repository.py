"""MySQL access for process-checkout. All money is in integer cents."""
from __future__ import annotations

import pymysql

from fashionstore_common.db import ER_DUP_ENTRY, RETRYABLE_ERRORS, error_code
from service import (CONFIRMED, OUT_OF_STOCK, REJECTED, CheckoutRequest, Outcome,
                     RetryableConflict)

_ORDER_COLUMNS = ("order_id, checkout_id, status, reason, user_sub, email, total_cents, "
                  "created_at, outcome_published_at")


def _to_outcome(row: dict) -> Outcome:
    return Outcome(
        checkout_id=row["checkout_id"],
        status=row["status"],
        reason=row["reason"],
        order_id=row["order_id"],
        user_sub=row["user_sub"],
        email=row["email"],
        total_cents=row["total_cents"],
        published=row["outcome_published_at"] is not None,
        occurred_at=row["created_at"],
    )


class CheckoutRepository:
    def __init__(self, conn):
        self.conn = conn

    # -- reads -------------------------------------------------------------
    def find_order(self, checkout_id: str) -> Outcome | None:
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT {_ORDER_COLUMNS} FROM orders WHERE checkout_id = %s", (checkout_id,))
            row = cur.fetchone()
        self.conn.commit()  # end the read snapshot so later reads see new commits
        return _to_outcome(row) if row else None

    def get_prices(self, skus: list[str]) -> dict[str, int]:
        if not skus:
            return {}
        placeholders = ", ".join(["%s"] * len(skus))
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT sku, price_cents FROM products WHERE active = TRUE AND sku IN ({placeholders})",
                tuple(skus))
            rows = cur.fetchall()
        self.conn.commit()
        return {r["sku"]: int(r["price_cents"]) for r in rows}

    # -- writes ------------------------------------------------------------
    def place_order(self, req: CheckoutRequest, prices: dict[str, int], total: int,
                    payment_ref: str) -> Outcome:
        """Insert a CONFIRMED order and decrement stock atomically, or return a REJECTED outcome."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO orders (checkout_id, user_sub, email, status, total_cents, payment_ref) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (req.checkout_id, req.user_sub, req.email, CONFIRMED, total, payment_ref))
                order_id = cur.lastrowid
                for item in req.items:  # already sorted by SKU
                    updated = cur.execute(
                        "UPDATE inventory SET qty = qty - %s WHERE sku = %s AND qty >= %s",
                        (item.qty, item.sku, item.qty))
                    if updated != 1:
                        self.conn.rollback()
                        return self.record_rejection(req, total, OUT_OF_STOCK, payment_ref)
                    cur.execute(
                        "INSERT INTO order_items (order_id, sku, qty, unit_price_cents) VALUES (%s, %s, %s, %s)",
                        (order_id, item.sku, item.qty, prices[item.sku]))
                cur.execute("UPDATE checkouts SET status = %s, reason = NULL WHERE checkout_id = %s",
                            (CONFIRMED, req.checkout_id))
            self.conn.commit()
        except pymysql.err.MySQLError as exc:
            self.conn.rollback()
            return self._handle_write_error(exc, req.checkout_id)
        return self._load(req.checkout_id)

    def record_rejection(self, req: CheckoutRequest, total: int, reason: str,
                         payment_ref: str | None) -> Outcome:
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO orders (checkout_id, user_sub, email, status, reason, total_cents, payment_ref) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (req.checkout_id, req.user_sub, req.email, REJECTED, reason, total, payment_ref))
                cur.execute("UPDATE checkouts SET status = %s, reason = %s WHERE checkout_id = %s",
                            (REJECTED, reason, req.checkout_id))
            self.conn.commit()
        except pymysql.err.MySQLError as exc:
            self.conn.rollback()
            return self._handle_write_error(exc, req.checkout_id)
        return self._load(req.checkout_id)

    def mark_published(self, checkout_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET outcome_published_at = CURRENT_TIMESTAMP(3) "
                "WHERE checkout_id = %s AND outcome_published_at IS NULL", (checkout_id,))
        self.conn.commit()

    # -- helpers -----------------------------------------------------------
    def _load(self, checkout_id: str) -> Outcome:
        outcome = self.find_order(checkout_id)
        if outcome is None:
            raise RuntimeError(f"order for {checkout_id} vanished after commit")
        return outcome

    def _handle_write_error(self, exc: Exception, checkout_id: str) -> Outcome:
        code = error_code(exc)
        if code == ER_DUP_ENTRY:
            # A concurrent delivery of the same checkout won the UNIQUE key: use its outcome.
            return self._load(checkout_id)
        if code in RETRYABLE_ERRORS:
            raise RetryableConflict(str(exc)) from exc
        raise exc
