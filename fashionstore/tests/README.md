# Tests

For the prepared 300-VU browsing presentation, use the [Mac watcher + CloudShell load commands](../docs/stress-demo.md). The `stress` profile is browse-only; it has not been run against the current rebuild.

## Offline (no AWS, run in CI)

| What | Where | Command | Count |
| --- | --- | --- | --- |
| Terraform decisions + wiring (mocked provider) | `infra/terraform/**/tests/*.tftest.hcl` | `make tf-test` | 33 runs |
| Lambdas against real MySQL 8 (oversell race, idempotency, notifier dedup, report CSV, payment, contracts) | `functions/*/tests` | `make py-test` | 57 |
| store-api against Testcontainers MySQL | `apps/store-api/src/test` | `make api-test` | 24 |
| storefront unit tests | `apps/storefront/tests` | `make web-test` | 17 |
| Browser journeys, mocked backend | `tests/e2e/specs` | `make e2e` | 4 |

## Live (against the deployed demo stack)

Setup once per window: `make test-users EMAILS="a@you b@you a+decline@you" TEST_USER_PASSWORD=...`
and `cd tests/e2e && npm ci` (the token helper uses its Playwright).

| What | Where | Command |
| --- | --- | --- |
| One checkout through SQS → Lambda → RDS → SNS → email | `infrastructure/smoke-test.sh` | `make smoke` |
| Only CloudFront is public | `infrastructure/verify-private-resources.sh`, `security/test_origin_access.py` | `make verify-private`, `make live-test` |
| 401 without a valid **access** token, forged/ID tokens refused | `security/test_authentication.py` | `make live-test` |
| Shopper B can't see or reuse shopper A's checkout/order | `security/test_ownership.py` | `make live-test` |
| Checkout confirms, stock drops, retry is idempotent, decline path, 90/10 split | `correctness/test_checkout_live.py` | `make live-test` |
| DLQ redrive becomes an order | `failure/test_dlq_redrive.py` | `make live-test` |
| Payment outage → SQS retry; poison → DLQ | `failure/test_worker_retry.py` | `FS_ALLOW_CHAOS=1` / `FS_RUN_SLOW=1 make live-test` |
| SQS outage in store-api → reconciler sends later | `failure/test_dispatch_recovery.py` | `FS_ALLOW_CHAOS=1 make live-test` |
| Notifier outage → exactly one email later | `failure/test_notification_recovery.py` | `FS_ALLOW_CHAOS=1 make live-test` |
| Same browser journeys on CloudFront + real Cognito | `tests/e2e` | `make e2e-live` |
| Load: browse, checkout, flash sale | `tests/load` | `make load-browse|load-checkout|load-flash PROFILE=demo` |

Live env vars: `FS_USER_A_EMAIL`, `FS_USER_B_EMAIL`, `FS_TEST_PASSWORD`, optional
`FS_DECLINE_EMAIL` (see `conftest.py`); for Playwright `E2E_USER_EMAIL`, `E2E_USER_PASSWORD`,
`E2E_DECLINE_EMAIL`, `E2E_DECLINE_PASSWORD`. Chaos tests change the stack on purpose
(Lambda concurrency 0, a bogus queue URL) and restore it in `finally`; run them one at a time.

Tokens: Cognito puts the `fashionstore-api/*` scopes only in tokens from the OAuth
flow, so `e2e/tools/get-token.mjs` signs in through the hosted UI with PKCE in
headless Chromium. `load/make-tokens.sh N` does that for N load-test users.
