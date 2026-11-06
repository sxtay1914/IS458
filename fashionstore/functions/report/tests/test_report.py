import csv
import io
from datetime import date, datetime, timezone
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from handler import generate, report_date

BUCKET = "fs-reports-test"


def insert_order(conn, checkout_id, status, created_at, lines):
    with conn.cursor() as cur:
        total = sum(q * p for _, q, p in lines)
        cur.execute("INSERT INTO orders (checkout_id, user_sub, email, status, total_cents, created_at) "
                    "VALUES (%s, 'u', 'a@example.com', %s, %s, %s)", (checkout_id, status, total, created_at))
        oid = cur.lastrowid
        for sku, qty, price in lines:
            cur.execute("INSERT INTO order_items VALUES (%s, %s, %s, %s)", (oid, sku, qty, price))
    conn.commit()
    return oid


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="ap-southeast-1")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        yield client


def read_csv(s3, key):
    return list(csv.DictReader(io.StringIO(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode())))


def test_report_date_defaults_to_yesterday_utc():
    now = datetime(2026, 11, 12, 0, 30, tzinfo=timezone.utc)
    assert report_date({}, now) == date(2026, 11, 11)
    assert report_date({"date": "today"}, now) == date(2026, 11, 12)
    assert report_date({"date": "2026-11-01"}, now) == date(2026, 11, 1)


def test_sales_and_stock_csv_match_orders(db, new_conn, s3):
    conn = new_conn()
    day = "2026-11-11 10:00:00"
    first = insert_order(conn, "00000000-0000-4000-8000-000000000001", "CONFIRMED", day,
                 [("DRS-001-M", 2, 5990), ("BAG-001", 1, 6990)])
    second = insert_order(conn, "00000000-0000-4000-8000-000000000002", "CONFIRMED", day, [("DRS-001-M", 1, 5990)])
    insert_order(conn, "00000000-0000-4000-8000-000000000003", "REJECTED", day, [("FLASH-001", 1, 9990)])
    insert_order(conn, "00000000-0000-4000-8000-000000000004", "CONFIRMED", "2026-11-12 00:00:00",
                 [("TOP-001-S", 1, 2990)])  # next day: excluded

    summary = generate(conn, s3, BUCKET, date(2026, 11, 11))

    sales = read_csv(s3, "reports/sales/dt=2026-11-11/sales.csv")
    assert [(r["sku"], r["order_id"], r["units"], r["revenue_cents"]) for r in sales] == [
        ("DRS-001-M", str(first), "2", "11980"), ("BAG-001", str(first), "1", "6990"),
        ("DRS-001-M", str(second), "1", "5990")]
    assert all(r["order_date"] == "2026-11-11" for r in sales)
    assert summary["revenue_cents"] == 17970 + 6990

    root = Path(__file__).resolve().parents[3]
    query = (root / "infra/terraform/modules/analytics/main.tf").read_text().split(
        'resource "aws_athena_named_query" "daily_revenue"', 1)[1].split("<<-SQL", 1)[1].split("\n  SQL", 1)[0]
    # Run the shipped Athena aggregation with MySQL's bigint spelling and a fixed clock.
    with conn.cursor() as cur:
        cur.execute("CREATE TEMPORARY TABLE sales (dt VARCHAR(10), order_id VARCHAR(20), revenue_cents VARCHAR(20))")
        cur.executemany("INSERT INTO sales VALUES (%s, %s, %s)",
                        [(r["order_date"], r["order_id"], r["revenue_cents"]) for r in sales])
        cur.execute(query.replace("AS bigint", "AS SIGNED").replace("current_date", "DATE '2026-11-12'"))
        daily = cur.fetchone()
        cur.execute((root / "database/queries/verify-report-totals.sql").read_text())
        expected = next(r for r in cur.fetchall() if r["order_date"] == date(2026, 11, 11))
        assert daily["orders"] == expected["confirmed_orders"] == 2
        assert int(daily["revenue_sgd"] * 100) == int(expected["revenue_cents"]) == summary["revenue_cents"]

    stock = read_csv(s3, "reports/stock/dt=2026-11-11/stock.csv")
    assert len(stock) == 10 and stock[0]["sku"] == "BAG-001" and stock[0]["qty"] == "40"
    assert list(stock[0].keys()) == ["sku", "name", "category", "qty", "updated_at"]


def test_empty_day_writes_header_only(db, new_conn, s3):
    summary = generate(new_conn(), s3, BUCKET, date(2026, 1, 1))
    body = s3.get_object(Bucket=BUCKET, Key=summary["keys"]["sales"])["Body"].read().decode()
    assert body == "order_date,sku,category,order_id,units,revenue_cents\n"
    assert summary["revenue_cents"] == 0
