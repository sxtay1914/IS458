# Lambda functions (Python 3.12, arm64)

| Function | Trigger | In VPC | What it guarantees |
| --- | --- | --- | --- |
| `process-checkout` | SQS `checkout-requests` (batch ≤ 5, partial failures) | yes | One order per `checkout_id` (UNIQUE key); no oversell (conditional `UPDATE … WHERE qty >= ?`, SKUs locked in sorted order); multi-line checkouts are all-or-nothing; a publish failure is retried without decrementing stock twice |
| `payment-api` | Sync invoke from process-checkout | no | Same decision and `payment_ref` for the same checkout (retry-safe). Decline with `+decline` in the email, amount > `MAX_AMOUNT_CENTS`, or `DECLINE_PERCENT` |
| `notifier` | SNS `checkout-status` (async, 2 retries, then `notifier-failures` SQS) | yes | One email per checkout under duplicate or concurrent delivery (UNIQUE row + 120 s lease). A crash between SES send and the SENT update can cause duplicate delivery on retry; `attempts > 1` records retries and possible duplicates, not a fixed duplicate limit |
| `report` | EventBridge Scheduler 00:30 UTC daily, or manual `{"date": "today"}` | yes | Sales and stock CSVs under `reports/<table>/dt=YYYY-MM-DD/` that match the Athena tables |

`common/fashionstore_common` (DB connection with secret rotation handling) is copied into every package by `scripts/package-functions.sh`.

Sales CSVs keep one row per order and product, including `order_id`. Athena counts distinct order IDs for the daily order total and sums line revenue, so multi-product orders count once.

## Tests

Tests run against a real MySQL 8 database built from `database/migrations` (a throwaway schema per run). Set `TEST_DB_HOST`/`TEST_DB_PASSWORD` if MySQL isn't on `127.0.0.1` with root/root.

```bash
make db-local-up
pip install -r functions/requirements-dev.txt
make py-test
```

The headline tests are `test_flash_sale_never_oversells` (120 shoppers race for 50 units across 10 parallel workers, which gives exactly 50 confirmed, 70 rejected and stock 0), `test_concurrent_duplicates_of_one_checkout_yield_one_order`, `test_publish_failure_keeps_order_and_retry_republishes` and `test_concurrent_deliveries_send_one_email`.
