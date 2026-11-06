# FashionStore Part B: phased implementation plan

Scope: the Part B implementation architecture only, in AWS `ap-southeast-1`, built with Terraform, on a US$100 budget. Part A stays documentation.

## Decisions locked in

| # | Decision | Replaces in the slides |
| --- | --- | --- |
| D1 | Terraform for all AWS resources; a separate `bootstrap` stack keeps state, CI access and budgets alive between demo stacks | "CloudFormation, delete each session" (slides 15, 20) |
| D2 | EKS managed node group of t3.medium, ASG 1 / 2 / 3, `ignore_changes` on `desired_size` so Terraform does not fight Cluster Autoscaler | 2× t3.small |
| D3 | CloudFront **VPC origin** to an **internal** ALB in the private app subnets, HTTP origin, ALB SG allows only the CloudFront origin-facing prefix list | Public ALB + secret header |
| D4 | SES sandbox; every demo recipient address verified before Phase 5 | n/a |
| D5 | Flyway owns the schema (`database/migrations/V00x__*.sql`), run as a Kubernetes Job | n/a |
| D6 | `UNIQUE (checkout_id)` on `orders` and `notification_log` | "one order per checkout" enforced only in code |
| D7 | Stock decrement is `UPDATE inventory SET qty = qty - ? WHERE sku = ? AND qty >= ?`, and an affected-row count of 0 means REJECTED | n/a |
| D8 | One reconciler in store-api sweeps both sides (pending checkouts never enqueued, committed outcomes never published to SNS) with `SELECT … FOR UPDATE SKIP LOCKED` | Dispatch-side only |
| D9 | v1 ×2 and v2 ×1 behind two **weighted** target groups (90/10) on one ALB listener rule | Pilot = pod count only |
| D10 | S3 gateway endpoint (free); everything else leaves through the single NAT | n/a |
| D11 | GitHub Actions authenticates with OIDC (plan role on PRs, apply role on `main`); there are no long-lived keys | n/a |
| D12 | Budget alerts at 50% and 80% of $100 (actual) plus 100% forecast, in the bootstrap stack so they survive teardown | n/a |
| D13 | `process-checkout` reserved concurrency 5 to protect the db.t4g.micro | Already in slides |
| D14 | The demo stack lives for 5 days, then `destroy` | n/a |
| D15 | UC4 wording becomes "one email per checkout, with a crash window that can produce at most one logged duplicate" | "exactly one email" |

Change slides 15, 19 and 20 to match D1 to D3 and D15 before you submit.

## The ordering problem in the "checkout first" approach

The coordinator suggested proving the Lambda checkout path before EKS. **[Likely]** That breaks down on one detail. RDS sits in an isolated subnet with no route in, so nothing on a laptop can run Flyway against it. The cheapest thing that can reach it is a Kubernetes Job on the EKS cluster. So the order is: **create the EKS cluster as bare infrastructure on Day 1** (it takes about 15 minutes and needs no app), use it to run migrations and seeds, then prove the Lambda checkout path with scripts. The store-api comes after that.

## Before the 5-day window (Phase 0, about $0)

Everything that does not need the cloud is done first, so the 5 paid days go on integration and evidence instead of fixing bugs.

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

## The 5-day window

Cost runs about $7 to $9 a day **[Likely]**: EKS control plane $2.40, 2× t3.medium about $2.50, NAT about $1.50 plus data, ALB about $0.60, RDS t4g.micro about $0.60, and the public IPv4 address. Five days is roughly $40 to $45, which leaves headroom for one rebuild.

### Day 1: foundation and data (Phases 1 and 2a)

| Terraform module | Contents |
| --- | --- |
| `network` | VPC 10.10.0.0/16, three layers × two AZs, one NAT in AZ A, S3 gateway endpoint, SGs (**done in this drop**) |
| `registry` | ECR `store-api`, lifecycle keeps the last 5 images |
| `database` | RDS MySQL 8.0 db.t4g.micro single-AZ in the isolated subnets, `manage_master_user_password`, 1-day backups, `skip_final_snapshot` |
| `eks` | Cluster, OIDC provider, access entries, node group in **AZ A private subnet only**, nodes get the `app` SG |
| `observability` | 7-day log groups, alarms (DLQ depth > 0, Lambda errors, RDS CPU), SNS ops topic |

Exit: the `database-migration` Job runs Flyway to V003, and `seed-demo` loads products and inventory. `verify-stock.sql` returns the seeded totals.

### Day 1 to 2: checkout pipeline (Phase 2b), the most graded part

| Item | Detail |
| --- | --- |
| `messaging` | `checkout-requests` SQS (visibility timeout 6× the Lambda timeout, `maxReceiveCount` 5), `checkout-dlq`, SNS `checkout-status`, SNS `ops-alerts` |
| `functions` | `process-checkout` (in VPC, reserved concurrency 5, SQS batch 1 to 5 with `ReportBatchItemFailures`), `payment-api` (no VPC, deterministic outcome by `checkout_id` hash) |
| Transaction | Insert `orders` (UNIQUE checkout_id) → conditional decrement per line → write outcome row → commit → publish to SNS. A duplicate key on insert means "already processed": re-publish the stored outcome and ack |

Exit, with evidence saved to `evidence/`: `concurrent-stock-test.py` (200 checkouts for 50 units → exactly 50 CONFIRMED, stock 0, never negative), `duplicate-checkout-test.py`, `duplicate-message-test.py`, and `dlq-redrive-test.py`.

### Day 2: store-api on EKS (Phase 3)

| Item | Detail |
| --- | --- |
| Add-ons (Helm) | metrics-server, Cluster Autoscaler (IRSA), AWS Load Balancer Controller (IRSA) used **only** for `TargetGroupBinding` |
| `delivery` (ALB half) | Internal ALB in the private subnets, two IP target groups `v1`/`v2`, listener rule `/api/*` with weights 90/10 |
| Workloads | `deployment-v1` ×2, `deployment-v2` ×1, HPA on v1, IRSA role for SQS send and secret read, the reconciler on a `@Scheduled` loop with SKIP LOCKED |
| CI | GitHub Actions builds the image, pushes to ECR, and runs `kubectl apply -k overlays/demo` |

Exit: an in-cluster curl to the ALB hits both versions in about a 90/10 split over 1,000 requests, and a checkout via the API reaches CONFIRMED.

### Day 3: edge, identity and UI (Phase 4)

| Item | Detail |
| --- | --- |
| `identity` | Cognito user pool, public app client with PKCE (no secret), hosted domain, callback = CloudFront URL |
| `delivery` (edge half) | Private S3 with OAC for the storefront, CloudFront VPC origin to the internal ALB for `/api/*`, caching disabled on `/api/*`, SPA fallback |
| store-api | JWT validation against the Cognito JWKS, ownership check on orders |

Exit: the e2e `shopper-journey.spec.ts` passes through the CloudFront URL. `origin-access-test.py` shows the S3 URL returns 403 and the ALB has no public DNS resolution.

### Day 4: notifications, reporting and the pilot (Phase 5)

| Item | Detail |
| --- | --- |
| Notifier | SNS → `notifier` λ (in VPC) → insert `notification_log` (UNIQUE checkout_id) → SES send → mark sent |
| Report | EventBridge daily schedule (plus a manual invoke for the demo) → `report` λ → CSV to the reports S3 bucket (lifecycle) → Athena workgroup with 7-day results expiry |
| Pilot | Shift the weights to 50/50, then to 0/100 and back; record the ALB target-group metrics |

Exit: `notification-recovery-test.py` and `verify-report-totals.sql` match the orders table.

### Day 5: load, failure and evidence, then destroy (Phase 6)

1. k6 `smoke`, then `demo` profiles for browse, checkout and flash-sale. Capture p95 latency, HPA and CA scaling events, and SQS age-of-oldest-message.
2. Failure drills: kill a store-api pod, force payment failures into the DLQ and redrive them, and break SNS publish to show the reconciler recovering.
3. Export the evidence: screenshots, k6 summaries, CloudWatch graphs, Cost Explorer for the window, and `terraform state list`.
4. `make destroy-demo`, then check that no ENIs, EIPs, load balancers or snapshots are left. Keep the `bootstrap` stack until grading is over.

## Teardown rules

* Delete the Kubernetes objects that own AWS resources (TargetGroupBinding, and any Service of type LoadBalancer) **before** `terraform destroy`. Otherwise the destroy stalls on ENIs and security groups.
* Lambda ENIs in the VPC can take up to about 20 minutes to release after the functions are deleted. If the subnet deletion times out, re-run the destroy.
* RDS uses `skip_final_snapshot = true` in demo, and ECR uses `force_delete = true`.

## Risks to watch

| Risk | Mitigation |
| --- | --- |
| VPC-origin ALB security group: CloudFront may connect from its service-managed SG (`CloudFront-VPCOrigins-Service-SG`) instead of the prefix list | The network module accepts extra source SG ids. If CloudFront returns 502 or 504 on `/api/*`, add that SG's id **[Guessing]** on which one applies until we test it |
| t3.medium pod density (17 pods per node with the VPC CNI default) | 2 nodes are enough for 3 API pods plus add-ons; CA can add a third |
| NAT data charges from in-VPC Lambdas calling SQS, SNS, SES and Secrets Manager | Small at demo volume; interface endpoints cost more than they save here |
| SES sandbox | Use only verified addresses in tests |
| Student accounts sometimes block Budgets or OIDC providers | Apply bootstrap in Phase 0 so you find out early |
