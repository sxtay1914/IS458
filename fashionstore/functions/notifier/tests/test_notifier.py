import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from fashionstore_common import testing
from handler import InFlight, Notifier, handle, render
from repository import NotificationRepository


class FakeSes:
    def __init__(self, fail_times=0, delay=None):
        self.sent = []
        self.fail_times = fail_times
        self.delay = delay
        self._lock = threading.Lock()

    def send(self, to, subject, body):
        if self.delay:
            self.delay.wait(2)
        with self._lock:
            if self.fail_times:
                self.fail_times -= 1
                raise ConnectionError("SES throttled")
            self.sent.append((to, subject, body))
            return f"ses-{len(self.sent)}"


def event(status="CONFIRMED", reason=None, checkout_id=None):
    return {"schema_version": 1, "checkout_id": checkout_id or str(uuid.uuid4()), "status": status,
            "reason": reason, "order_id": 42, "user_sub": "u1", "email": "shopper@example.com",
            "total_cents": 12980, "occurred_at": "2026-11-11T11:11:02.315Z"}


def log_row(db, checkout_id):
    return testing.query(db, "SELECT * FROM notification_log WHERE checkout_id = %s", (checkout_id,))[0]


def test_render_confirmed_and_rejected():
    subject, body = render(event())
    assert "#42" in subject and "S$129.80" in body
    _, body = render(event("REJECTED", "OUT_OF_STOCK"))
    assert "sold out" in body


def test_render_escapes_html():
    e = event()
    e["order_id"] = "<script>"
    _, body = render(e)
    assert "<script>" not in body and "&lt;script&gt;" in body


def test_sends_once_and_skips_duplicates(db, new_conn):
    ses = FakeSes()
    n = Notifier(NotificationRepository(new_conn()), ses)
    e = event()
    assert n.notify(e) == "SENT"
    assert n.notify(e) == "SKIPPED_DUPLICATE"
    assert len(ses.sent) == 1
    row = log_row(db, e["checkout_id"])
    assert row["status"] == "SENT" and row["attempts"] == 1 and row["ses_message_id"] == "ses-1"


def test_ses_failure_is_logged_and_retry_succeeds(db, new_conn):
    ses = FakeSes(fail_times=1)
    n = Notifier(NotificationRepository(new_conn()), ses)
    e = event("REJECTED", "PAYMENT_DECLINED")
    with pytest.raises(ConnectionError):
        n.notify(e)
    assert log_row(db, e["checkout_id"])["status"] == "FAILED"
    assert n.notify(e) == "SENT"
    row = log_row(db, e["checkout_id"])
    assert row["status"] == "SENT" and row["attempts"] == 2 and len(ses.sent) == 1


def test_concurrent_deliveries_send_one_email(db, new_conn):
    gate = threading.Event()
    ses = FakeSes(delay=gate)
    e = event()
    notifiers = [Notifier(NotificationRepository(new_conn()), ses) for _ in range(6)]

    def run(n):
        try:
            return n.notify(e)
        except InFlight:
            return "IN_FLIGHT"

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run, n) for n in notifiers]
        import time
        time.sleep(0.5)
        gate.set()
        results = sorted(f.result() for f in futures)

    assert results.count("SENT") == 1
    assert set(results) <= {"SENT", "IN_FLIGHT", "SKIPPED_DUPLICATE"}
    assert len(ses.sent) == 1


def test_crash_after_send_is_one_logged_duplicate(db, new_conn):
    """Lease expiry after a crash lets a retry send again; attempts records it."""
    ses = FakeSes()
    repo = NotificationRepository(new_conn())
    e = event()
    assert repo.claim(e["checkout_id"], e["email"], "CONFIRMED") == "CLAIMED"
    ses.send(e["email"], "s", "b")  # sent, then the Lambda "crashes" before mark_sent
    conn = new_conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE notification_log SET claimed_until = NOW(3) - INTERVAL 1 SECOND WHERE checkout_id = %s",
                    (e["checkout_id"],))
    conn.commit()

    assert Notifier(NotificationRepository(new_conn()), ses).notify(e) == "SENT"
    assert log_row(db, e["checkout_id"])["attempts"] == 2
    assert len(ses.sent) == 2


def test_unexpired_lease_raises_in_flight(db, new_conn):
    e = event()
    NotificationRepository(new_conn()).claim(e["checkout_id"], e["email"], "CONFIRMED")
    with pytest.raises(InFlight):
        Notifier(NotificationRepository(new_conn()), FakeSes()).notify(e)


def test_sns_records_are_unwrapped(db, new_conn):
    ses = FakeSes()
    e = event()
    records = {"Records": [{"Sns": {"Message": json.dumps(e)}}, {"Sns": {"Message": json.dumps(e)}}]}
    assert handle(records, Notifier(NotificationRepository(new_conn()), ses)) == ["SENT", "SKIPPED_DUPLICATE"]


def test_rejects_unknown_event_shape(db, new_conn):
    with pytest.raises(ValueError):
        Notifier(NotificationRepository(new_conn()), FakeSes()).notify({"schema_version": 2})


def test_ses_sender_builds_request():
    from handler import SesSender

    class Client:
        def send_email(self, **kw):
            self.kw = kw
            return {"MessageId": "m-1"}

    c = Client()
    assert SesSender("orders@example.com", "cfg", client=c).send("to@example.com", "S", "<p>B</p>") == "m-1"
    assert c.kw["Destination"] == {"ToAddresses": ["to@example.com"]} and c.kw["ConfigurationSetName"] == "cfg"
