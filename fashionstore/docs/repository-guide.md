# Repository guide

What every folder and file is for, what is finished, and what is left.
Status as of 2026-11-06. "A" is the platform builder, "B" is the data and app builder.

Based on the [13-page PDF](<../../FashionStore repository guide.pdf>); the checked current tree and corrections are in [Project Directory Structure](../../FashionStore_Project_Directory_Structure.md). The Git root is `IS458/`; application paths here are relative to `fashionstore/`, and commands run there. The latest verification includes 24 API integration tests, 57 Lambda tests, 21 storefront unit tests, four mocked browser journeys, 31 live API checks and three live browser journeys. Four optional live API tests and one browser fault-injection journey were skipped. Sanitized AWS results and screenshots are under `docs/report/evidence/2026-11-06/`; the first demo teardown is in progress, followed by an owner-requested full restart with the new UI/images. The restarted demo remains running for owner review with a manual teardown reminder.

## How the pieces fit

```
Browser ──HTTPS──> CloudFront ──OAC──────────> S3 (storefront build)
                       │
                       └─/api/*─VPC origin──> internal ALB ──90/10──> store-api v1 / v2 pods (EKS)
                                                                          │  JWT from Cognito
                                                                          ▼
                       RDS MySQL <── process-checkout λ <── SQS checkout-requests (+ DLQ)
                          ▲               │ invoke payment-api λ
                          │               ▼
                          └── notifier λ <── SNS checkout-status
                                  │
                                  └──> SES email          report λ (daily) ──> S3 CSV ──> Athena
```

A checkout: store-api saves it as PENDING and sends it to SQS. process-checkout takes it,
reads prices from MySQL and asks payment-api, then conditionally decrements stock and writes
the order in one transaction, and publishes the outcome to SNS. The notifier deduplicates
email attempts, with a send/SENT-update crash window. The storefront polls the API, which
reads checkout status from MySQL; SNS does not push status into the API.

---

## Top level

| File | What it does |
| --- | --- |
| `README.md` | Front page: status table, offline test commands, the deploy runbook |
| `Makefile` | Every command the team runs. `make help` lists them. Offline: `test`, `tf-test`, `py-test`, `api-test`, `web-test`, `e2e`. AWS: `bootstrap`, `deploy-demo`, `k8s-config`, `addons`, `db-migrate-remote`, `push-api`, `k8s-apply`, `deploy-storefront`, `smoke`, `verify-private`, `live-test`, `e2e-live`, `load-*`, `destroy-demo` |
| `.gitignore` | Keeps Terraform state, `terraform.tfvars`, `backend.hcl`, build output, `node_modules` and generated env files out of git |
| `../.github/workflows/ci.yml` (Git root) | On every PR: Terraform fmt/validate/test, Lambda pytest on a MySQL service, Kustomize render, store-api tests + Docker build, storefront tests + build, Playwright e2e, k6 script parse |
| `../.github/workflows/terraform-plan.yml` (Git root) | On PRs touching application infrastructure/functions or plan tooling: assumes the read-only GitHub OIDC role and runs `terraform plan` (no PR comment) |

The workflow files are at the Git root under `.github/workflows/`, with shell steps running from `fashionstore/` and action input paths relative to the Git root. GitHub can discover them once pushed; actual runner execution is not yet verified. The AWS plan job requires repository variables `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET`. There is no CD workflow.

## docs/

| File | What it does |
| --- | --- |
| `implementation-plan.md` | Locked decisions, who does what, the phased demo sequence with exit criteria and manual teardown after owner review, the manual teardown checklist, risks |
| `repository-guide.md` | This file |

## contracts/ — the agreement between the two halves

| File | What it does |
| --- | --- |
| `openapi.yaml` | Every `/api/*` endpoint, request and response. store-api implements it, the storefront calls it |
| `events/checkout-request.schema.json` | The SQS message store-api sends to process-checkout |
| `events/checkout-status.schema.json` | The SNS message with the outcome (CONFIRMED or REJECTED + reason) |
| `examples/*.json` | One valid example of each message; tests validate them against the schemas |
| `README.md` | Who produces and consumes what, and the rules (at-least-once, dedupe on `checkout_id`, never trust prices in a message) |

## database/ — MySQL schema (Flyway)

| File | What it does |
| --- | --- |
| `migrations/V001__catalog_and_cart.sql` | `products`, `inventory` (with a `CHECK qty >= 0` backstop), `carts`, `cart_items` |
| `migrations/V002__checkout_and_orders.sql` | `checkouts` (PENDING rows, request JSON, `enqueued_at` for the reconciler), `orders` (UNIQUE `checkout_id`), `order_items` |
| `migrations/V003__dispatch_and_notification.sql` | `notification_log` (UNIQUE `checkout_id`, lease column `claimed_until`) and `reconciliation_log` (what the reconciler re-sent) |
| `seeds/products.sql`, `seeds/inventory.sql` | 10 demo products; `FLASH-001` has 50 units for the flash-sale test. Re-runnable |
| `queries/verify-stock.sql` | Evidence: stock never negative, confirmed units match decrements |
| `queries/verify-idempotency.sql` | Evidence: one order/notification row per checkout; retries flag possible email duplicates |
| `queries/verify-report-totals.sql` | Evidence: the daily report equals the orders table |
| `README.md` | How migrations run (a Kubernetes Job, because RDS is in isolated subnets) |

## functions/ — the four Lambdas (Python 3.12, arm64)

| Path | What it does |
| --- | --- |
| `common/fashionstore_common/db.py` | Opens the MySQL connection from the Secrets Manager secret; reconnects after a password rotation |
| `common/fashionstore_common/testing.py` | Test helper: builds a throwaway database from `database/migrations` |
| `process-checkout/handler.py` | SQS entry point; reports failed messages one by one (`batchItemFailures`) so only they are retried |
| `process-checkout/service.py` | The checkout rules: validate, price from the DB, pay, place or reject, publish |
| `process-checkout/repository.py` | The SQL: insert order (UNIQUE key = idempotency), conditional `UPDATE inventory … WHERE qty >= ?` in SKU order (prevents oversell and reduces deadlock risk; conflicts are retried) |
| `process-checkout/tests/` | 32 tests, including 120 buyers racing for 50 units (exactly 50 confirmed) and duplicate deliveries |
| `payment-api/handler.py` | Fake payment provider. Same answer for the same checkout; declines `+decline` emails |
| `notifier/handler.py`, `repository.py` | SNS → claim a `notification_log` row with a lease → send via SES → mark SENT. Duplicate deliveries are suppressed; a crash after sending can cause duplicate email |
| `notifier/templates/*.html` | The confirmation and rejection emails |
| `report/handler.py`, `queries/*.sql` | Daily sales and stock CSVs into S3, partitioned for Athena |
| `*/requirements.txt` | Runtime dependencies packed into each zip |
| `requirements-dev.txt` | pytest, boto3, moto, jsonschema, PyMySQL for local tests |
| `README.md` | What each function guarantees and how to test |

## apps/store-api/ — the REST API (Spring Boot 3.5, Java 21)

| Path | What it does |
| --- | --- |
| `pom.xml`, `mvnw`, `.mvn/` | Maven build; the wrapper means no Maven install is needed |
| `Dockerfile`, `.dockerignore` | Two-stage image: build the jar, run it on a JRE as a non-root user |
| `src/main/java/.../StoreApiApplication.java` | Starts the app in UTC with scheduling on |
| `configuration/AppProperties.java` | All `fashionstore.*` settings in one typed record |
| `configuration/AwsConfig.java` | SQS and SNS clients |
| `configuration/DataSourceConfig.java` | Reads the DB password from Secrets Manager when `DB_SECRET_ARN` is set |
| `configuration/SecurityConfig.java` | Catalogue public; cart and checkout need `checkout.write`; orders need `orders.read`; everything else denied |
| `auth/CognitoAccessTokenValidator.java` | Accepts only access tokens issued to our client (rejects ID tokens) |
| `auth/UserEmailResolver.java`, `CurrentUser.java` | Who is calling and their email |
| `catalog/*` | `GET /api/products`, `/api/products/{sku}` with stock |
| `cart/*` | `GET/PUT /api/cart`, stored in MySQL |
| `checkout/CheckoutService.java` | Save PENDING + clear cart in one transaction, then send to SQS. Same Idempotency-Key = same checkout |
| `checkout/CheckoutController.java`, `CheckoutRepository.java`, `CheckoutStatus.java` | The endpoints and SQL for checkouts |
| `orders/*` | `GET /api/orders`, `/api/orders/{id}`, only your own |
| `messaging/Reconciler.java` | Every 15 s: re-send checkouts that never reached SQS, re-publish outcomes never published. `SKIP LOCKED` so 3 pods don't collide |
| `messaging/Sqs*`, `Sns*`, `InMemoryMessaging.java` | Real AWS senders, plus in-memory fakes for local runs and tests |
| `common/*` | Error JSON with `correlation_id`, the `X-Correlation-Id` filter, `/api/version` (v1 or v2) |
| `src/main/resources/application.yml` | Maps environment variables (from the Kubernetes ConfigMap) to settings; readiness checks the DB |
| `src/main/resources/application-local.yml` | Local profile: no AWS, messages kept in memory |
| `src/test/java/...` | 24 integration tests on a real MySQL container (security, cart, idempotency, SQS outage, reconciler, ownership) |
| `README.md` | Package map and how the checkout stays correct |

## apps/storefront/ — the website (React 19, Vite)

| Path | What it does |
| --- | --- |
| `package.json`, `package-lock.json` | Dependencies and scripts: `dev`, `build`, `test`, `typecheck` |
| `index.html`, `vite.config.ts`, `tsconfig.json` | Vite entry, dev proxy of `/api` to :8080, test setup |
| `public/config.json` | Runtime settings; the deploy script overwrites it with real Cognito values |
| `public/images/*.svg` | Supplied product illustrations, served from S3 through CloudFront |
| `.env.example` | Explains why there are no build-time env vars |
| `src/main.tsx`, `App.tsx` | Loads `config.json`, then the routes |
| `src/auth/pkce.ts` | Sign-in with Cognito: PKCE challenge, state check, code exchange |
| `src/auth/AuthContext.tsx` | Keeps tokens in sessionStorage; `useAuth()` |
| `src/api/client.ts`, `index.ts`, `ApiContext.tsx` | Typed calls for every endpoint, bearer token attached |
| `src/hooks/useCart.ts` | Server-side cart |
| `src/hooks/useCheckoutPolling.ts` | Polls a checkout with backoff until it is decided |
| `src/pages/*` | Products, product details, bag, checkout, status, orders, order details, sign-in callback |
| `src/pages/checkoutKey.ts` | One Idempotency-Key per checkout attempt, reused on retry |
| `src/components/*` | Navigation, footer with API version, product cards, cart lines, checkout steps and status, icons and not-found page |
| `src/styles/app.css`, `src/types/index.ts` | Styling and shared types |
| `tests/*` | 21 vitest tests (RFC 7636 PKCE vector, API client, polling, retry keeps the same key, components) |
| `README.md` | Layout and local dev |

## infra/terraform/ — all AWS resources

| Path | What it does |
| --- | --- |
| `bootstrap/` | Run once, local state. State bucket, GitHub OIDC with plan and apply roles, $100 budget with 50 / 80 / forecast-100 alerts |
| `environments/demo/main.tf` | Wires all modules into the demo stack |
| `environments/demo/variables.tf`, `terraform.tfvars.example` | Inputs: owner, expiry date, SES sender and recipients, EKS admin ARNs, v1/v2 weights |
| `environments/demo/outputs.tf` | URLs, ARNs and `app_config` that scripts read |
| `environments/demo/backend.hcl.example`, `providers.tf`, `versions.tf` | S3 backend with lockfile, AWS provider with default tags |
| `environments/demo/tests/stack.tftest.hcl` | Whole-stack composition test |
| `modules/network` | VPC, public/private/isolated subnets in 2 AZs, one NAT, S3 gateway endpoint, security groups |
| `modules/registry` | ECR repo for store-api (immutable tags, scan on push) |
| `modules/database` | RDS MySQL 8.4 db.t4g.micro, password managed in Secrets Manager |
| `modules/messaging` | SQS checkout queue + DLQ, notifier-failures queue, SNS topics |
| `modules/analytics` | Reports bucket, Athena workgroup, Glue tables |
| `modules/functions` | The four Lambdas, their roles, triggers, schedule, SES identities |
| `modules/eks` | EKS 1.34, t3.small node group 1/2/3, IRSA roles |
| `modules/delivery` | Internal ALB, v1/v2 target groups 90/10, S3 + OAC, CloudFront with VPC origin, `spa-rewrite.js` |
| `modules/identity` | Cognito pool, hosted UI (classic), PKCE client, API scopes |
| `modules/observability` | 11 alarms to email, one dashboard |
| `modules/private-bucket` | Helper for private, encrypted, TLS-only buckets |
| `modules/*/tests/*.tftest.hcl` | Checks each locked decision with a mocked AWS provider |
| `tests/mocks/aws.tfmock.hcl` | Realistic fake ARNs/ids shared by all tests |
| `README.md` | Module table, network map, first-run steps |

## platform/ — what runs on EKS

| Path | What it does |
| --- | --- |
| `kubernetes/base/namespace.yaml`, `service-account.yaml` | Namespace and the IRSA service account for store-api |
| `kubernetes/base/deployment-v1.yaml`, `deployment-v2.yaml` | store-api v1 (2 pods) and v2 (1 pod), probes on `/actuator/health/*` |
| `kubernetes/base/service.yaml`, `target-group-binding.yaml` | Services, and bindings that register pod IPs into the Terraform-made target groups |
| `kubernetes/base/hpa-v1.yaml` | Autoscaling for v1, plus a disruption budget |
| `kubernetes/base/configmap.yaml` | Defaults shared by both versions |
| `kubernetes/overlays/demo/*` | Fills in real values from `terraform output` (`generated/*.env`, written by `make k8s-config`) |
| `kubernetes/jobs/database-migration.yaml` | Flyway Job that migrates RDS from inside the cluster |
| `kubernetes/jobs/seed-demo.yaml` | Job that loads the seeds |
| `addons/*/values.yaml` | Helm settings for metrics-server, Cluster Autoscaler, AWS Load Balancer Controller |

## scripts/

| File | What it does |
| --- | --- |
| `package-functions.sh` | Builds `build/functions/*.zip` (code + common + dependencies), byte-for-byte repeatable |
| `render-k8s-config.sh` | Writes the overlay's `generated/*.env` from `terraform output` |
| `select-kinds.py` | Filters rendered YAML by kind (used before the migration Job) |
| `build-push-api.sh` | Builds the store-api image for amd64 and pushes it to ECR |
| `deploy-storefront.sh` | Builds the SPA, writes `config.json`, uploads to S3 with cache headers, invalidates CloudFront |
| `create-test-users.sh` | Creates confirmed Cognito test shoppers |

## tests/

| Path | What it does |
| --- | --- |
| `README.md` | Every test, where it lives, how to run it |
| `infrastructure/smoke-test.sh` | Live: one checkout straight into SQS, expects CONFIRMED and an empty DLQ |
| `infrastructure/verify-private-resources.sh` | Live: ALB internal, RDS private, S3 403, CloudFront 200 and HTTPS redirect |
| `e2e/playwright.config.ts`, `package.json` | Playwright setup; mock mode by default, live mode with `E2E_BASE_URL` |
| `e2e/specs/shopper-journey.spec.ts` | Browse → sign in → add to bag → checkout → confirmed → orders; retry keeps the key |
| `e2e/specs/rejected-checkout.spec.ts` | Declined payment shows a clear message; signed-out users are asked to sign in |
| `e2e/support/mock-backend.ts` | Fake Cognito and API inside the browser for offline runs |
| `e2e/support/session.ts`, `env.ts` | Sign-in steps and test users for both modes |
| `e2e/tools/get-token.mjs` | Gets real tokens through the hosted UI for the live pytest and k6 tests |
| `conftest.py`, `pytest.ini`, `requirements-live.txt` | Shared live-test setup; everything skips unless `FS_BASE_URL` is set |
| `security/test_authentication.py` | 401 without a token, with a forged token, or with an ID token |
| `security/test_ownership.py` | Shopper B can't read or reuse shopper A's checkout or order |
| `security/test_origin_access.py` | Only CloudFront is reachable; SPA deep links work; API 404s stay JSON |
| `correctness/test_checkout_live.py` | Confirm, stock drops, idempotent retry, empty cart, decline path, 90/10 split |
| `failure/test_dlq_redrive.py` | A message moved back from the DLQ becomes an order |
| `failure/test_worker_retry.py` | Payment outage recovers through SQS retry (chaos); poison message reaches the DLQ (slow) |
| `failure/test_dispatch_recovery.py` | store-api can't reach SQS → reconciler sends it later (chaos) |
| `failure/test_notification_recovery.py` | Notifier outage recovery and notification-log deduplication (chaos) |
| `load/browse.js`, `checkout.js`, `flash-sale.js` | k6 load tests with p95 thresholds; flash sale checks no oversell |
| `load/lib/common.js`, `profiles/*.json`, `make-tokens.sh` | Shared helpers, smoke and demo load sizes, token generation for N users |

---

## What is done

| Area | Evidence |
| --- | --- |
| Terraform: bootstrap, 10 service modules + bucket helper, demo stack | 33 `terraform test` runs green against a mocked provider; `fmt` and `validate` clean |
| Database schema and seeds | Flyway V001–V003 migrate cleanly on MySQL 8.0 |
| Four Lambdas | 57 pytest tests green on real MySQL 8, including the oversell race and duplicate delivery |
| store-api | 24 integration tests green on Testcontainers MySQL; the jar starts locally and serves the catalogue |
| storefront | 21 unit tests, typecheck and production build green |
| Browser journeys | 4 Playwright tests green against the mocked backend, 12 of 12 on a 3x repeat |
| Live tests and load scripts | Written; all 35 live tests skip cleanly offline; the public-endpoint auth tests passed against a locally running store-api |
| Kubernetes, Helm, deploy scripts, CI | Written; the overlay renders with `kubectl kustomize` |

## What still needs to be done

Bootstrap is complete. The first demo passed the live API/browser checks and is being removed. The owner requested a complete restart for review, followed by a teardown reminder; the original five-day runtime is superseded. The repository and monorepo workflow configuration already exist; the workflow changes still need pushing and a GitHub run.

| # | Step | Who | Notes |
| --- | --- | --- | --- |
| 1 | Use the existing `sxtay1914/IS458` repo; configure bootstrap `github_repository` accordingly. Set `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET` after step 2; push the root-level workflows and verify their first GitHub run | A | Repo already exists; current local source includes changes beyond the earlier push |
| 2 | Bootstrap completed; fill `environments/demo/terraform.tfvars` (owner, `expires_on`, SES sender and recipients, your IAM ARN in `eks_admin_principal_arns`, your IP in `eks_public_access_cidrs`) | A | |
| 3 | `make init-demo deploy-demo` | A | **Never applied yet.** Expect a few fixes on the first real apply |
| 4 | Click the SES verification emails for sender and recipients | B | Unverified recipients get no email in the sandbox |
| 5 | `make k8s-config addons db-migrate-remote db-seed-remote`, then `make smoke` | A | |
| 6 | `make push-api TAG=v1` and `TAG=v2`, then `make k8s-config V1_TAG=v1 V2_TAG=v2 k8s-apply` | B builds, A applies | **The Docker image has never been built**: Docker Hub and ECR Public were blocked here |
| 7 | `make deploy-storefront verify-private` | B | If `/api/*` returns 502/504, add the CloudFront VPC-origin SG to `alb_extra_source_security_group_ids` |
| 8 | `make test-users`, then `make live-test e2e-live` | B | First real run of `get-token.mjs`; the hosted-UI field names are an educated guess |
| 9 | Chaos and slow tests: `FS_ALLOW_CHAOS=1 FS_RUN_SLOW=1 make live-test`, one at a time | A + B | They change the stack and restore it |
| 10 | Load: `make load-browse load-checkout load-flash PROFILE=smoke`, then `PROFILE=demo` | A + B | k6 has not been run here; reseed FLASH-001 before each flash sale |
| 11 | Pilot: set weights 50/50, then 0/100 and back in tfvars, `terraform apply`, record the target-group metrics | A | |
| 12 | Report: invoke `report` with `{"date": "today"}`, run the Athena named queries | B | |
| 13 | Save evidence (screenshots, k6 summaries, CloudWatch graphs, Cost Explorer, `terraform state list`) | A + B | No `evidence/` folder yet |
| 14 | After owner review: teardown checklist in the plan, then check the bill | A | |

Gaps that are known and not built: no CD workflow (deploys are `make` commands run by hand), and
the Kubernetes YAML has only been rendered and parsed, not schema-checked with kubeconform.
