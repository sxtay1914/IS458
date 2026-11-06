"""report: daily sales and stock CSVs for Athena.

Triggered by an EventBridge Scheduler schedule (daily, for the previous UTC
day) or invoked manually with {"date": "YYYY-MM-DD"} or {"date": "today"}.
Writes:
  s3://$REPORTS_BUCKET/reports/sales/dt=YYYY-MM-DD/sales.csv
  s3://$REPORTS_BUCKET/reports/stock/dt=YYYY-MM-DD/stock.csv
The Glue tables use partition projection on dt, so new days need no crawler.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import pathlib
from datetime import date, datetime, timedelta, timezone

import boto3

from fashionstore_common import db

log = logging.getLogger()
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

QUERIES = pathlib.Path(__file__).resolve().parent / "queries"
SALES_COLUMNS = ["order_date", "sku", "category", "order_id", "units", "revenue_cents"]
STOCK_COLUMNS = ["sku", "name", "category", "qty", "updated_at"]


def report_date(event: dict | None, now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    requested = (event or {}).get("date")
    if requested in (None, "", "yesterday"):
        return (now - timedelta(days=1)).date()
    if requested == "today":
        return now.date()
    return date.fromisoformat(requested)


def run_query(conn, name: str, params: dict | None = None) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute((QUERIES / f"{name}.sql").read_text(), params or {})
        rows = list(cur.fetchall())
    conn.commit()
    return rows


def to_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in columns})
    return buf.getvalue()


def generate(conn, s3, bucket: str, day: date) -> dict:
    start = datetime(day.year, day.month, day.day)
    sales = run_query(conn, "sales", {"start": start, "end": start + timedelta(days=1)})
    stock = run_query(conn, "stock")
    keys = {
        "sales": f"reports/sales/dt={day.isoformat()}/sales.csv",
        "stock": f"reports/stock/dt={day.isoformat()}/stock.csv",
    }
    s3.put_object(Bucket=bucket, Key=keys["sales"], Body=to_csv(sales, SALES_COLUMNS).encode(),
                  ContentType="text/csv")
    s3.put_object(Bucket=bucket, Key=keys["stock"], Body=to_csv(stock, STOCK_COLUMNS).encode(),
                  ContentType="text/csv")
    summary = {
        "date": day.isoformat(),
        "sales_rows": len(sales),
        "revenue_cents": int(sum(int(r["revenue_cents"]) for r in sales)),
        "stock_rows": len(stock),
        "keys": keys,
    }
    log.info(json.dumps({"event": "report_written", **summary}))
    return summary


def lambda_handler(event, context):
    return generate(db.get_connection(), boto3.client("s3"), os.environ["REPORTS_BUCKET"], report_date(event))
