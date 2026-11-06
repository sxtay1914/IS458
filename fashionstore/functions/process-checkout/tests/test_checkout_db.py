"""Correctness tests against real MySQL 8: oversell, idempotency, atomicity, recovery."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from fakes import FakePayment, FakePublisher
from fashionstore_common import testing
from handler import process_records
from repository import CheckoutRepository
from service import CheckoutService


def request(sku="DRS-001-M", qty=1, checkout_id=None, items=None, email="shopper@example.com"):
    return {
        "schema_version": 1,
        "checkout_id": checkout_id or str(uuid.uuid4()),
        "user_sub": "user-1",
        "email": email,
        "items": items or [{"sku": sku, "qty": qty}],
        "requested_at": "2026-11-11T11:11:00Z",
    }


def stock(db, sku):
    return testing.query(db, "SELECT qty FROM inventory WHERE sku = %s", (sku,))[0]["qty"]


def orders(db, checkout_id=None):
    if checkout_id:
        return testing.query(db, "SELECT * FROM orders WHERE checkout_id = %s", (checkout_id,))
    return testing.query(db, "SELECT * FROM orders")


def make_service(new_conn, payment=None, publisher=None):
    return CheckoutService(CheckoutRepository(new_conn()), payment or FakePayment(), publisher or FakePublisher())


def test_confirmed_order_decrements_stock_and_publishes(db, new_conn):
    pub = FakePublisher()
    svc = make_service(new_conn, publisher=pub)
    msg = request(items=[{"sku": "DRS-001-M", "qty": 2}, {"sku": "BAG-001", "qty": 1}])

    outcome = svc.process(msg)

    assert outcome.status == "CONFIRMED"
    assert outcome.total_cents == 2 * 5990 + 6990
    assert stock(db, "DRS-001-M") == 98 and stock(db, "BAG-001") == 39
    items = testing.query(db, "SELECT sku, qty, unit_price_cents FROM order_items ORDER BY sku")
    assert [(i["sku"], i["qty"], i["unit_price_cents"]) for i in items] == [("BAG-001", 1, 6990), ("DRS-001-M", 2, 5990)]
    assert len(pub.events) == 1 and pub.events[0]["status"] == "CONFIRMED"
    assert orders(db, msg["checkout_id"])[0]["outcome_published_at"] is not None


def test_checkout_row_status_is_updated(db, new_conn):
    msg = request()
    conn = new_conn()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO checkouts (checkout_id, user_sub, email, request_json, enqueued_at) "
                    "VALUES (%s, 'user-1', 'shopper@example.com', %s, NOW(3))", (msg["checkout_id"], json.dumps(msg)))
    conn.commit()
    make_service(new_conn).process(msg)
    row = testing.query(db, "SELECT status FROM checkouts WHERE checkout_id = %s", (msg["checkout_id"],))[0]
    assert row["status"] == "CONFIRMED"


def test_duplicate_message_creates_one_order_and_one_decrement(db, new_conn):
    pub = FakePublisher()
    pay = FakePayment()
    svc = make_service(new_conn, payment=pay, publisher=pub)
    msg = request(qty=3)

    first = svc.process(msg)
    second = svc.process(msg)

    assert first.order_id == second.order_id
    assert len(orders(db, msg["checkout_id"])) == 1
    assert stock(db, "DRS-001-M") == 97
    assert len(pub.events) == 1, "already-published outcome must not be re-published"
    assert len(pay.calls) == 1


def test_concurrent_duplicates_of_one_checkout_yield_one_order(db, new_conn):
    msg = request(qty=1)
    services = [make_service(new_conn) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda s: s.process(msg), services))

    assert {o.order_id for o in outcomes} == {outcomes[0].order_id}
    assert len(orders(db, msg["checkout_id"])) == 1
    assert stock(db, "DRS-001-M") == 99


def test_flash_sale_never_oversells(db, new_conn):
    """120 shoppers race for 50 FLASH-001 units with 10 parallel workers."""
    seeded = stock(db, "FLASH-001")
    assert seeded == 50
    msgs = [request(sku="FLASH-001", qty=1) for _ in range(120)]
    services = [make_service(new_conn) for _ in range(10)]

    def worker(idx):
        svc = services[idx % 10]
        return [svc.process(m) for m in msgs[idx::10]]

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = [o for batch in pool.map(worker, range(10)) for o in batch]

    confirmed = [o for o in results if o.status == "CONFIRMED"]
    rejected = [o for o in results if o.status == "REJECTED"]
    assert len(confirmed) == 50
    assert len(rejected) == 70 and {o.reason for o in rejected} == {"OUT_OF_STOCK"}
    assert stock(db, "FLASH-001") == 0
    sold = testing.query(db, "SELECT COALESCE(SUM(oi.qty),0) AS n FROM order_items oi "
                             "JOIN orders o ON o.order_id = oi.order_id WHERE o.status='CONFIRMED' AND oi.sku='FLASH-001'")
    assert sold[0]["n"] == 50
    assert testing.query(db, "SELECT COUNT(*) AS n FROM orders")[0]["n"] == 120


def test_multi_item_shortage_rolls_back_every_line(db, new_conn):
    conn = new_conn()
    with conn.cursor() as cur:
        cur.execute("UPDATE inventory SET qty = 1 WHERE sku = 'TOP-001-S'")
    conn.commit()
    msg = request(items=[{"sku": "DRS-001-M", "qty": 2}, {"sku": "TOP-001-S", "qty": 2}])

    outcome = make_service(new_conn).process(msg)

    assert outcome.status == "REJECTED" and outcome.reason == "OUT_OF_STOCK"
    assert stock(db, "DRS-001-M") == 100, "earlier line must be rolled back"
    assert stock(db, "TOP-001-S") == 1
    assert testing.query(db, "SELECT COUNT(*) AS n FROM order_items")[0]["n"] == 0


def test_payment_declined_rejects_without_touching_stock(db, new_conn):
    outcome = make_service(new_conn, payment=FakePayment(approve=False)).process(request(qty=2))
    assert outcome.status == "REJECTED" and outcome.reason == "PAYMENT_DECLINED"
    assert stock(db, "DRS-001-M") == 100


def test_unknown_sku_is_rejected_without_payment(db, new_conn):
    pay = FakePayment()
    outcome = make_service(new_conn, payment=pay).process(request(sku="NOPE-404"))
    assert outcome.status == "REJECTED" and outcome.reason == "UNKNOWN_SKU"
    assert pay.calls == []


def test_publish_failure_keeps_order_and_retry_republishes(db, new_conn):
    pub = FakePublisher(fail_times=1)
    svc = make_service(new_conn, publisher=pub)
    msg = request()

    with pytest.raises(ConnectionError):
        svc.process(msg)
    row = orders(db, msg["checkout_id"])[0]
    assert row["status"] == "CONFIRMED" and row["outcome_published_at"] is None
    assert stock(db, "DRS-001-M") == 99

    svc.process(msg)  # SQS redelivery
    assert len(pub.events) == 1
    assert orders(db, msg["checkout_id"])[0]["outcome_published_at"] is not None
    assert stock(db, "DRS-001-M") == 99, "retry must not decrement again"


def test_handler_reports_only_failed_records(db, new_conn):
    svc = make_service(new_conn)
    records = [
        {"messageId": "ok-1", "body": json.dumps(request())},
        {"messageId": "bad-json", "body": "{not json"},
        {"messageId": "bad-schema", "body": json.dumps({"schema_version": 1})},
        {"messageId": "ok-2", "body": json.dumps(request(sku="BAG-001"))},
    ]
    result = process_records(records, svc)
    assert result == {"batchItemFailures": [{"itemIdentifier": "bad-json"}, {"itemIdentifier": "bad-schema"}]}
    assert len(orders(db)) == 2
