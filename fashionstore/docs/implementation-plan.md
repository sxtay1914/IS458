# FashionStore Part B: phased implementation plan

Scope: the Part B implementation architecture only, in AWS `ap-southeast-1`, built with Terraform, on a US$100 budget. Part A stays documentation.

See the [current directory structure](../../FashionStore_Project_Directory_Structure.md) and [repository guide](repository-guide.md) for implemented paths and remaining gaps. Commands run from `fashionstore/` inside `sxtay1914/IS458`.

## Build status (2026-11-10)

Setup completed at 13:55 (UTC+8): [storefront](https://d1oj35ccg258u3.cloudfront.net) and [local dashboard](http://localhost:8501) are running for owner use. [Redeployment evidence](report/evidence/2026-11-10-restart/redeploy.json) records 63 creates, zero changes/deletes and retention of the existing RDS/VPC, orders and stock. The owner reversed teardown after 25 Lambda/dependent and 38 compute/delivery resources were deleted; the final 79-resource destroy plan was never applied. Teardown is paused, with no automatic shutdown.

Two workers are Ready, all three add-ons are available, both API rollouts use `demo-20261109-49cc9e8`, and the storefront build/S3 upload completed. Existing SES/SNS verification was retained. No migration/seed Jobs, purchases, pytest, browser checks, chaos or load drills were run in this rebuild: the owner requested setup only. Deployment readiness does not establish current API/browser functionality. See the [dashboard guide](../dashboard/README.md) and [presentation outline](presentation-content-structure.md).

The earlier [November 10 00:37 results](report/evidence/2026-11-10-restart/results.json) remain unchanged: 31 API passes/four skips, three browser passes/one skip, seven private-access passes, 112 offline dashboard passes and two successful tab renders. That deployment's no-change Terraform plan and successful cart purchase are historical, not current retests. Existing source-build tag: [`v0.1.0`](https://github.com/sxtay1914/IS458/tree/v0.1.0).

The first AWS demo passed 31 live API tests and three live browser journeys; four optional API chaos/slow tests and one browser fault-injection journey were skipped. Local checks passed: 33 Terraform mock-provider test runs, 57 Lambda tests against MySQL 8.4, 24 API integration tests, 21 storefront tests, typecheck/build and four mocked browser journeys. The API Docker image was built for amd64 and deployed. Flyway V001–V003 migrated RDS with verified TLS, and reporting through Lambda/S3/Athena passed. Sanitized results and screenshots are in `docs/report/evidence/2026-11-06/`. CD, load drills and the full submission report remain outstanding.

The restarted demo with the supplied UI and illustrations passed 31 live API tests, with four optional tests skipped. Its final browser run passed two journeys, failed one on a cart database deadlock and intentionally skipped one. All nine image URLs returned HTTP 200 and matched the source files; ten catalogue images loaded with no mobile horizontal overflow. These historical results are preserved in [restart evidence](report/evidence/2026-11-07-restart/results.json).

On 2026-11-08, the cart deadlock was reproduced locally against MySQL 8.4 and fixed by using `READ_COMMITTED` only for `CartRepository.replace`. The baseline regression suite had one failure and two passes; after the change, all 27 API tests passed, including concurrent empty-cart fills, rollback on an invalid item and complete same-shopper replacements. See [fix evidence](report/evidence/2026-11-08-cart-deadlock/results.json). The earlier November 10 00:37 browser run verified the corrected purchase flow.

The previous demo was torn down on 2026-11-07. Its historical [teardown verification](report/evidence/2026-11-07-restart/teardown.json) records empty Terraform state and 23 checks with zero remaining resources or errors. Bootstrap state, GitHub OIDC roles and the US$100 alert budget were retained. Budget notifications are not a spending cap. The current instruction is to leave the rebuilt session running, preserve existing orders/stock and perform no tests.

The November 7 inventory recorded three stopped Assignment3 EC2 instances, three 8 GB gp3 volumes and one unattached Elastic IP outside the demo; no fresh account-wide inventory is claimed here. The preflight billing snapshot for November 1–9 showed about US$6.30 usage offset by credits. It is delayed data and does not establish the remaining credit balance or final restart cost.

Change from the original plan: Cognito `USER_PASSWORD_AUTH` was removed. Its access tokens carry only `aws.cognito.signin.user.admin`, never the `fashionstore-api/*` scopes the API requires, so scripted tests sign in through the hosted UI with PKCE instead (`tests/e2e/tools/get-token.mjs`).

## Decisions locked in

| # | Decision | Replaces in the slides |
| --- | --- | --- |
| D1 | Terraform for all AWS resources; a separate `bootstrap` stack keeps state, CI access and budgets alive between demo stacks | "CloudFormation, delete each session" (slides 15, 20) |
| D2 | EKS managed node group of t3.small, ASG 1 / 2 / 3, `ignore_changes` on `desired_size` so Terraform does not fight Cluster Autoscaler | 2× t3.small |
| D3 | CloudFront **VPC origin** to an **internal** ALB in the private app subnets, HTTP origin, ALB SG allows the CloudFront origin-facing prefix list plus its private VPC-origin service security group | Public ALB + secret header |
| D4 | SES sandbox; verify the sender and real recipients, or use SES simulator recipients for tests | n/a |
| D5 | Flyway owns the schema (`database/migrations/V00x__*.sql`), run as a Kubernetes Job | n/a |
| D6 | `UNIQUE (checkout_id)` on `orders` and `notification_log` | "one order per checkout" enforced only in code |
| D7 | Stock decrement is `UPDATE inventory SET qty = qty - ? WHERE sku = ? AND qty >= ?`, and an affected-row count of 0 means REJECTED | n/a |
| D8 | One reconciler in store-api sweeps both sides (pending checkouts never enqueued, committed outcomes never published to SNS) with `SELECT … FOR UPDATE SKIP LOCKED` | Dispatch-side only |
| D9 | v1 ×2 and v2 ×1 behind two **weighted** target groups (90/10) on one ALB listener rule | Pilot = pod count only |
| D10 | S3 gateway endpoint (free); everything else leaves through the single NAT | n/a |
| D11 | Bootstrap creates OIDC plan and apply roles; the written plan workflow uses the PR role. Manual `make` deployment is current; no CD/apply workflow is implemented. No long-lived CI keys | n/a |
| D12 | Budget alerts at 50% and 80% of $100 (actual) plus 100% forecast, in the bootstrap stack so they survive teardown | n/a |
| D13 | SQS caps checkout workers at 5 to protect the db.t4g.micro; reservation is disabled for this account's concurrency quota of 10 | Already in slides |
| D14 | Current rebuild: retain orders/stock, setup only with no tests; teardown paused until requested again | n/a |
| D15 | UC4 wording becomes "deduplicated email attempts per checkout, with possible duplicate delivery if SES accepts mail before SENT is persisted; attempts are logged" | "exactly one email" |

Change slides 15, 19 and 20 to match D1 to D3 and D15 before you submit.

## The ordering problem in the "checkout first" approach

The coordinator suggested proving the Lambda checkout path before EKS. **[Likely]** That breaks down on one detail. RDS sits in an isolated subnet with no route in, so nothing on a laptop can run Flyway against it. The cheapest thing that can reach it is a Kubernetes Job on the EKS cluster. So the order is: **create the EKS cluster as bare infrastructure at the start of the demo** (it takes about 15 minutes and needs no app), use it to run migrations and seeds, then prove the Lambda checkout path with scripts. The store-api comes after that.

## Who does what (two builders)

Split by layer, and meet at two seams that you fix on day 0: `contracts/` (the API and event shapes) and the Terraform outputs that become environment variables (queue URL, topic ARN, DB secret ARN, subnet and SG ids). After that, neither person waits on the other's code, only on the seam.

**A: Platform (Terraform, EKS, delivery, CI)**. **B: Data and application (schema, Lambdas, store-api, UI, tests).** Swap the letters if your strengths are the other way round.

| When | A: Platform | B: Data and application |
| --- | --- | --- |
| Phase 0 | Apply `bootstrap`. Write the `registry`, `database`, `eks`, `observability`, `messaging` and `functions` modules (`terraform validate` only). Root-level workflow definitions use IS458 monorepo paths; verify their first GitHub run, configure plan on PR, manual apply | Write `contracts/` first and agree on them with A. Flyway V001 to V003 and seeds. The `process-checkout` and `payment-api` handlers plus pytest on local MySQL. Correctness test scripts |
| Phase 0 | `delivery`, `identity` and `analytics` modules. Helm values for the 3 add-ons. Kustomize base and overlay | store-api (catalog, cart, checkout acceptance, reconciler with SKIP LOCKED) with Testcontainers. Storefront against a mocked API. `notifier` and `report` handlers |
| Demo setup | `deploy-demo` for network, database, eks and registry. Run the migration and seed Jobs | Build and package the Lambdas. Run checks against the real RDS through the Job |
| Demo checkout | `messaging` and `functions` apply, alarms, DLQ | Run the concurrent-stock, duplicate and DLQ tests and save the evidence |
| Demo API | Add-ons, internal ALB, weighted target groups, TargetGroupBinding, IRSA | Push the store-api image, deploy v1 and v2, prove the 90/10 split and a checkout via the API |
| Demo edge | Cognito, S3 + OAC, CloudFront VPC origin, any SG fix | JWT validation and ownership checks, storefront build and upload, Playwright e2e |
| Demo features | SNS → notifier wiring, SES identities, EventBridge schedule, Athena | Notification and reporting tests, the pilot weight shifts |
| End of demo | Cost Explorer export, CloudWatch graphs, **manual teardown** | k6 runs, failure drills, evidence write-up |

Sync points: end of Phase 0 (contracts frozen, `make validate` and the local tests green) and each demo phase (check against the exit criteria).

## Before the demo (Phase 0)

Finish offline work before provisioning the demo. Collect integration evidence, hand the running session to the owner for testing, then remind them to tear down afterwards.

| Work | Owner | Exit criterion |
| --- | --- | --- |
| Repo skeleton per the directory tree, `.gitignore`, Makefile | | `make fmt validate` passes |
| `contracts/`: OpenAPI and the two event JSON schemas, plus examples | | Examples validate against the schemas in CI |
| `database/migrations` V001 to V003 with D6 and D7, plus seeds | | `flyway migrate` passes on local MySQL 8 in Docker |
| `functions/*` handlers with pytest against local MySQL | | Duplicate-message and concurrent-stock tests pass locally |
| `apps/store-api` with Testcontainers MySQL | | Cart, checkout acceptance and reconciler tests pass |
| `apps/storefront` against a mocked API | | Builds to static `dist/` |
| **Apply `bootstrap`** (state bucket, OIDC roles, budget) | | Budget alert email confirmed; `terraform init` on `demo` works |
| Verify SES recipient addresses | | Each address shows "Verified" |

## Demo sequence (no five-day runtime)

The original five-day cost estimate is superseded. Keep the runtime short, export evidence and manually destroy when the owner finishes testing. US$100 budget alerts do not enforce a spending cap.

### Foundation and data (Phases 1 and 2a)

| Terraform module | Contents |
| --- | --- |
| `network` | VPC 10.10.0.0/16, three layers × two AZs, one NAT in AZ A, S3 gateway endpoint, SGs |
| `registry` | ECR `store-api`, lifecycle keeps the last 5 images |
| `database` | RDS MySQL 8.4 db.t4g.micro single-AZ in the isolated subnets, `manage_master_user_password`, 1-day backups, `skip_final_snapshot` |
| `eks` | Cluster, OIDC provider, access entries, node group in **AZ A private subnet only**, nodes get the `app` SG |
| `observability` | 7-day log groups, alarms (DLQ depth > 0, Lambda errors, RDS CPU), SNS ops topic |

Exit: the `database-migration` Job runs Flyway to V003, and `seed-demo` loads products and inventory. `verify-stock.sql` returns the seeded totals.

### Checkout pipeline (Phase 2b), the most graded part

| Item | Detail |
| --- | --- |
| `messaging` | `checkout-requests` SQS (visibility timeout 6× the Lambda timeout, `maxReceiveCount` 5), `checkout-dlq`, SNS `checkout-status`, SNS `ops-alerts` |
| `functions` | `process-checkout` (in VPC, SQS maximum concurrency 5 without reservation on this low-quota account, SQS batch 1 to 5 with `ReportBatchItemFailures`), `payment-api` (no VPC, deterministic outcome by `checkout_id` hash) |
| Transaction | Insert `orders` (UNIQUE checkout_id) → conditional decrement per line → write outcome row → commit → publish to SNS. A duplicate key on insert means "already processed": re-publish the stored outcome and ack |

Exit, with evidence saved to `evidence/`: `make smoke`, then `make load-flash` (every buyer races for FLASH-001 → confirmed never exceeds stock, stock never negative; the same race is proven offline by `test_flash_sale_never_oversells`), the idempotency tests in `tests/correctness/test_checkout_live.py`, and `tests/failure/test_dlq_redrive.py`.

### Store-api on EKS (Phase 3)

| Item | Detail |
| --- | --- |
| Add-ons (Helm) | metrics-server, Cluster Autoscaler (IRSA), AWS Load Balancer Controller (IRSA) used **only** for `TargetGroupBinding` |
| `delivery` (ALB half) | Internal ALB in the private subnets, two IP target groups `v1`/`v2`, listener rule `/api/*` with weights 90/10 |
| Workloads | `deployment-v1` ×2, `deployment-v2` ×1, HPA on v1, IRSA role for SQS send and secret read, the reconciler on a `@Scheduled` loop with SKIP LOCKED |
| CI / deployment | Written CI builds/tests the image; manual `make push-api` and `make k8s-apply` push/deploy. Earlier builds passed six CI jobs; new-commit CI results are not yet recorded here |

Exit: an in-cluster curl to the ALB hits both versions in about a 90/10 split over 1,000 requests, and a checkout via the API reaches CONFIRMED.

### Edge, identity and UI (Phase 4)

| Item | Detail |
| --- | --- |
| `identity` | Cognito user pool, public app client with PKCE (no secret), hosted domain, callback = CloudFront URL |
| `delivery` (edge half) | Private S3 with OAC for the storefront, CloudFront VPC origin to the internal ALB for `/api/*`, caching disabled on `/api/*`, SPA fallback |
| store-api | JWT validation against the Cognito JWKS, ownership check on orders |

Exit: `make e2e-live` (`tests/e2e/specs/shopper-journey.spec.ts`) passes through the CloudFront URL. `tests/security/test_origin_access.py` (or `make verify-private`) shows the S3 URL returns 403 and the ALB is internal/private; public API access goes through CloudFront.

### Notifications, reporting and the pilot (Phase 5)

| Item | Detail |
| --- | --- |
| Notifier | SNS → `notifier` λ (in VPC) → insert `notification_log` (UNIQUE checkout_id) → SES send → mark sent |
| Report | EventBridge daily schedule (plus a manual invoke for the demo) → `report` λ → CSV to the reports S3 bucket (lifecycle) → Athena workgroup with 7-day results expiry |
| Pilot | Shift the weights to 50/50, then to 0/100 and back; record the ALB target-group metrics |

Exit: `tests/failure/test_notification_recovery.py` (chaos) and `database/queries/verify-report-totals.sql` matches the orders table.

### End of demo: load, failure and evidence, then manual destroy (Phase 6)

1. k6 `smoke`, then `demo` profiles for browse, checkout and flash-sale. Capture p95 latency, HPA and CA scaling events, and SQS age-of-oldest-message.
2. Failure drills: kill a store-api pod, force payment failures into the DLQ and redrive them, and break SNS publish to show the reconciler recovering.
3. Export the evidence: screenshots, k6 summaries, CloudWatch graphs, Cost Explorer for the window, and `terraform state list`.
4. After the owner finishes testing, follow the staged teardown checklist below and check for residual demo resources. Keep `bootstrap` while its state is still needed, then remove it last.

## Teardown rules (manual destroy)

The stack is destroyed by hand. Do it in this order, or `terraform destroy` stalls on ENIs and security groups that Terraform does not own.

1. Export the evidence first: the Cost Explorer view for the window, CloudWatch graphs, k6 summaries and the Athena query results.
2. Delete both TargetGroupBindings and wait for their deletion while the LB controller is still running. Then `kubectl delete -k platform/kubernetes/overlays/demo` removes the remaining app resources.
3. `helm uninstall` the three add-ons.
4. Review and apply a targeted Terraform destroy plan for `module.functions.aws_lambda_function.this` and its dependants. Keep the Lambda execution roles and VPC-access policy attachments until AWS releases the Lambda ENIs. Review a separate plan to remove EKS, delivery and NAT resources while that cleanup proceeds; do not let it remove those Lambda permissions early.
5. Wait for the Lambda ENIs to disappear, then review and apply a full demo destroy plan. Do not force-delete service-managed ENIs. RDS uses `skip_final_snapshot = true`, and ECR and the report bucket use force delete. `make destroy-demo` does not implement the staged Lambda-permission retention above; it runs a single full destroy.
6. Verify the demo Terraform state is empty and no demo EC2 workers, load balancers, NAT gateways, Elastic IPs, ENIs, RDS instances/snapshots, CloudFront distribution/VPC origin or Lambda functions remain. Remove demo resources outside Terraform, including temporary operator credentials and leftover RDS log groups. If a CloudFront service security group remains orphaned, remove it only after verifying its VPC origin is absent and no ENIs use it. Retained bootstrap and unrelated account resources must be reported separately.
7. Once no further deployments or grading need the state, back it up, empty the state bucket and destroy bootstrap last. Budget alerts remain in bootstrap during demo cleanup.

Before each future deployment, configure a valid EKS admin principal, refresh the allowed IP and expiry date, reverify the recreated SES identity and discover the new CloudFront service security group. Refresh the ignored private demo inputs for that deployment; private configuration is not committed.

## Risks to watch

| Risk | Mitigation |
| --- | --- |
| VPC-origin ALB security group: CloudFront may connect from its service-managed SG (`CloudFront-VPCOrigins-Service-SG`) instead of the prefix list | The network module accepts extra source SG ids. If CloudFront returns 502 or 504 on `/api/*`, add that SG's id as confirmed during the first live AWS demo |
| t3.small pod density (11 pods per node with the VPC CNI default) | 2 nodes are enough for 3 API pods plus add-ons; CA can add a third |
| NAT data charges from in-VPC Lambdas calling SQS, SNS, SES and Secrets Manager | Small at demo volume; interface endpoints cost more than they save here |
| SES sandbox | Verify real recipient addresses or use SES simulator addresses in tests |
| Student accounts sometimes block Budgets or OIDC providers | Apply bootstrap in Phase 0 so you find out early |
