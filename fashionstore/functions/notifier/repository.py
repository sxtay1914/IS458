"""notification_log access: one row per checkout, claimed with a short lease.

claim() returns:
  "CLAIMED"   - this invocation owns the send (attempts was incremented)
  "SENT"      - already sent; skip (duplicate SNS delivery)
  "IN_FLIGHT" - another invocation holds an unexpired lease; retry later
"""
from __future__ import annotations

import time

import pymysql

from fashionstore_common.db import RETRYABLE_ERRORS, error_code

CLAIMED, SENT, IN_FLIGHT = "CLAIMED", "SENT", "IN_FLIGHT"


class NotificationRepository:
    def __init__(self, conn, lease_seconds: int = 120):
        self.conn = conn
        self.lease_seconds = int(lease_seconds)

    def claim(self, checkout_id: str, email: str, outcome: str) -> str:
        for attempt in range(1, 4):
            try:
                return self._claim_once(checkout_id, email, outcome)
            except pymysql.err.MySQLError as exc:
                if error_code(exc) not in RETRYABLE_ERRORS or attempt == 3:
                    raise
                time.sleep(0.05 * attempt)
        raise AssertionError("unreachable")

    def _claim_once(self, checkout_id: str, email: str, outcome: str) -> str:
        try:
            # Insert and claim in separate transactions: concurrent INSERT IGNOREs on the
            # same key take shared locks, and upgrading them in the same txn deadlocks.
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT IGNORE INTO notification_log (checkout_id, email, outcome) VALUES (%s, %s, %s)",
                    (checkout_id, email, outcome))
            self.conn.commit()
            with self.conn.cursor() as cur:
                won = cur.execute(
                    "UPDATE notification_log "
                    "SET status = 'SENDING', attempts = attempts + 1, last_error = NULL, "
                    "    claimed_until = CURRENT_TIMESTAMP(3) + INTERVAL %s SECOND "
                    "WHERE checkout_id = %s AND status <> 'SENT' "
                    "  AND (claimed_until IS NULL OR claimed_until < CURRENT_TIMESTAMP(3))",
                    (self.lease_seconds, checkout_id))
                if won == 1:
                    result = CLAIMED
                else:
                    cur.execute("SELECT status FROM notification_log WHERE checkout_id = %s", (checkout_id,))
                    result = SENT if cur.fetchone()["status"] == "SENT" else IN_FLIGHT
            self.conn.commit()
            return result
        except Exception:
            self.conn.rollback()
            raise

    def mark_sent(self, checkout_id: str, ses_message_id: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE notification_log SET status = 'SENT', ses_message_id = %s, "
                "sent_at = CURRENT_TIMESTAMP(3), claimed_until = NULL WHERE checkout_id = %s",
                (ses_message_id, checkout_id))
        self.conn.commit()

    def mark_failed(self, checkout_id: str, error: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE notification_log SET status = 'FAILED', last_error = %s, claimed_until = NULL "
                "WHERE checkout_id = %s", (error[:500], checkout_id))
        self.conn.commit()
