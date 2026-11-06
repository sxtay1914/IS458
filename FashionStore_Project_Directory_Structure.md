# FashionStore — Project Directory Structure

This monorepo supports the Part B implementation architecture on AWS Singapore (`ap-southeast-1`). Terraform provisions AWS resources; Kubernetes and Helm configure EKS workloads; application build steps produce the API image, Lambda packages and static UI.

The Part A production architecture is documentation only. Do not provision its extra services as part of the demo.

## Proposed technology choices

| Area | Proposed choice |
| --- | --- |
| Storefront | React + TypeScript, static build hosted in private S3 through CloudFront |
| Store API | Java + Spring Boot, containerised and deployed to EKS |
| Serverless functions | Python |
| Database | RDS MySQL |
| Infrastructure | Terraform |
| Workloads and add-ons | Kubernetes, Kustomize and Helm |
| Tests | JUnit, pytest, browser automation and k6 |

These application-language choices are recommendations, not requirements imposed by the diagram.

## Full directory tree

```text
fashionstore/
├── README.md
├── .gitignore
├── .env.example
├── Makefile
│
├── apps/
│   ├── storefront/
│   │   ├── README.md
│   │   ├── package.json
│   │   ├── package-lock.json
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── .env.example
│   │   ├── public/
│   │   │   └── images/
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── pages/
│   │   │   │   ├── ProductsPage.tsx
│   │   │   │   ├── ProductDetailsPage.tsx
│   │   │   │   ├── CartPage.tsx
│   │   │   │   ├── CheckoutPage.tsx
│   │   │   │   ├── CheckoutStatusPage.tsx
│   │   │   │   ├── OrdersPage.tsx
│   │   │   │   ├── OrderDetailsPage.tsx
│   │   │   │   └── AuthCallbackPage.tsx
│   │   │   ├── components/
│   │   │   │   ├── ProductCard.tsx
│   │   │   │   ├── CartItem.tsx
│   │   │   │   ├── CheckoutStatus.tsx
│   │   │   │   └── Navigation.tsx
│   │   │   ├── auth/                  # Cognito PKCE and session handling
│   │   │   ├── api/                   # HTTP client and API modules
│   │   │   ├── hooks/                 # Cart and checkout polling hooks
│   │   │   ├── types/
│   │   │   └── styles/
│   │   └── tests/                     # UI unit/component tests
│   │
│   └── store-api/
│       ├── README.md
│       ├── pom.xml
│       ├── mvnw
│       ├── mvnw.cmd
│       ├── .mvn/wrapper/
│       ├── Dockerfile
│       ├── .dockerignore
│       └── src/
│           ├── main/
│           │   ├── java/com/fashionstore/
│           │   │   ├── StoreApiApplication.java
│           │   │   ├── auth/          # Token validation and ownership
│           │   │   ├── catalog/       # Products, filters and stock views
│           │   │   ├── cart/          # Shopper cart operations
│           │   │   ├── checkout/      # Acceptance and status endpoints
│           │   │   ├── orders/        # Shopper order history/details
│           │   │   ├── messaging/     # Queue publishing and reconciliation
│           │   │   ├── configuration/
│           │   │   └── common/        # Errors and correlation IDs
│           │   └── resources/
│           │       ├── application.yml
│           │       └── application-local.yml
│           └── test/
│               ├── java/com/fashionstore/
│               └── resources/
│
├── functions/
│   ├── process-checkout/
│   │   ├── README.md
│   │   ├── handler.py
│   │   ├── service.py                # Idempotency, stock/order transaction
│   │   ├── repository.py
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── payment-api/
│   │   ├── README.md
│   │   ├── handler.py                # Deterministic, retry-safe simulation
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── notifier/
│   │   ├── README.md
│   │   ├── handler.py
│   │   ├── repository.py             # Notification deduplication/log
│   │   ├── requirements.txt
│   │   ├── templates/
│   │   │   ├── confirmed.html
│   │   │   └── rejected.html
│   │   └── tests/
│   └── report/
│       ├── README.md
│       ├── handler.py
│       ├── requirements.txt
│       ├── queries/
│       │   ├── sales.sql
│       │   └── stock.sql
│       └── tests/
│
├── contracts/
│   ├── README.md
│   ├── openapi.yaml
│   ├── events/
│   │   ├── checkout-request.schema.json
│   │   └── checkout-status.schema.json
│   └── examples/
│       ├── checkout-request.json
│       ├── checkout-confirmed.json
│       └── checkout-rejected.json
│
├── database/
│   ├── README.md
│   ├── migrations/                   # Canonical ordered schema migrations
│   │   ├── V001__catalog_and_cart.sql
│   │   ├── V002__checkout_and_orders.sql
│   │   └── V003__dispatch_and_notification.sql
│   ├── seeds/
│   │   ├── products.sql
│   │   └── inventory.sql
│   └── queries/
│       ├── verify-stock.sql
│       ├── verify-idempotency.sql
│       └── verify-report-totals.sql
│
├── infra/
│   └── terraform/
│       ├── README.md
│       ├── bootstrap/                # Separate persistent state foundation
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── modules/
│       │   ├── network/              # VPC, subnet pairs, routes, NAT, SGs
│       │   ├── identity/             # Cognito user pool/client/domain
│       │   ├── registry/             # ECR and last-five-image retention
│       │   ├── database/             # Single-AZ RDS, backups and secret
│       │   ├── eks/                  # Cluster, nodes, OIDC and access
│       │   ├── messaging/            # Checkout SQS, DLQ and SNS topics
│       │   ├── functions/            # Lambdas, roles and event bindings
│       │   ├── delivery/             # ALB, targets, S3, CloudFront OAC
│       │   ├── analytics/            # Schedule, report S3, Athena setup
│       │   └── observability/        # Log groups, alarms and budgets
│       └── environments/
│           └── demo/
│               ├── main.tf
│               ├── providers.tf
│               ├── versions.tf
│               ├── variables.tf
│               ├── outputs.tf
│               ├── backend.hcl.example
│               └── terraform.tfvars.example
│
├── platform/
│   ├── README.md
│   ├── addons/
│   │   ├── metrics-server/values.yaml
│   │   ├── cluster-autoscaler/values.yaml
│   │   └── aws-load-balancer-controller/values.yaml
│   └── kubernetes/
│       ├── base/
│       │   ├── kustomization.yaml
│       │   ├── namespace.yaml
│       │   ├── service-account.yaml  # API IRSA role annotation
│       │   ├── service.yaml
│       │   ├── configmap.yaml
│       │   ├── deployment-v1.yaml
│       │   ├── deployment-v2.yaml
│       │   ├── hpa-v1.yaml
│       │   └── target-group-binding.yaml
│       ├── overlays/
│       │   └── demo/
│       │       ├── kustomization.yaml
│       │       ├── configmap-patch.yaml
│       │       └── resource-limits-patch.yaml
│       └── jobs/
│           ├── database-migration.yaml
│           └── seed-demo.yaml
│
├── tests/
│   ├── README.md
│   ├── integration/
│   │   ├── api-database/
│   │   ├── checkout-pipeline/
│   │   ├── notification-pipeline/
│   │   └── reporting/
│   ├── e2e/
│   │   ├── playwright.config.ts
│   │   ├── shopper-journey.spec.ts
│   │   └── rejected-checkout.spec.ts
│   ├── correctness/
│   │   ├── concurrent-stock-test.py
│   │   ├── duplicate-checkout-test.py
│   │   └── duplicate-message-test.py
│   ├── security/
│   │   ├── authentication-test.py
│   │   ├── ownership-test.py
│   │   └── origin-access-test.py
│   ├── load/
│   │   ├── browse.js                # k6
│   │   ├── checkout.js
│   │   ├── flash-sale.js
│   │   └── profiles/
│   │       ├── smoke.json
│   │       └── demo.json
│   ├── failure/
│   │   ├── worker-retry-test.py
│   │   ├── dlq-redrive-test.py
│   │   ├── dispatch-recovery-test.py
│   │   └── notification-recovery-test.py
│   ├── infrastructure/
│   │   ├── smoke-test.sh
│   │   └── verify-private-resources.sh
│   └── fixtures/                   # Synthetic reusable test data
│
├── scripts/
│   ├── README.md
│   ├── check-prerequisites.sh
│   ├── build-artifacts.sh
│   ├── push-api-image.sh
│   ├── package-functions.sh
│   ├── provision-infra.sh
│   ├── install-addons.sh
│   ├── deploy-workloads.sh
│   ├── migrate-database.sh
│   ├── seed-demo.sh
│   ├── publish-storefront.sh
│   ├── deploy-demo.sh              # Orchestrates staged deployment
│   ├── smoke-test.sh
│   ├── collect-evidence.sh
│   └── destroy-demo.sh
│
├── local/
│   ├── README.md
│   ├── compose.yaml               # Local MySQL and chosen dependencies
│   └── .env.example
│
├── docs/
│   ├── architecture/
│   │   ├── implementation.drawio.svg
│   │   ├── production.drawio.svg
│   │   ├── data-model.md
│   │   ├── checkout-flow.md
│   │   └── decisions/
│   │       ├── 001-terraform-and-resource-ownership.md
│   │       ├── 002-checkout-consistency-and-recovery.md
│   │       └── 003-demo-production-tradeoffs.md
│   ├── runbooks/
│   │   ├── deployment.md
│   │   ├── dlq-redrive.md
│   │   ├── rollback.md
│   │   ├── backup-restore.md
│   │   └── teardown.md
│   ├── demo/
│   │   ├── presentation-script.md
│   │   └── pre-demo-checklist.md
│   └── report/
│       ├── FashionStore_Project_Report_Structure.md
│       ├── requirements-matrix.md
│       ├── test-plan.md
│       ├── test-results.md
│       ├── six-pillars.md
│       ├── contributions.md
│       ├── cost/
│       │   ├── assumptions.md
│       │   ├── demo-estimate.csv
│       │   ├── production-estimate.csv
│       │   └── actual-spend.csv
│       └── evidence/
│           ├── README.md
│           ├── ui/
│           ├── deployment/
│           ├── security/
│           ├── correctness/
│           ├── performance/
│           ├── scaling/
│           ├── recovery/
│           ├── analytics/
│           └── cost/
│
└── .github/
    └── workflows/
        ├── application-checks.yml
        ├── terraform-checks.yml
        └── deploy-demo.yml
```

Each Terraform module normally contains `main.tf`, `variables.tf`, `outputs.tf` and a short `README.md`. Split large module files by concern only when useful. The tree lists planned files, not already implemented code.

## Component responsibilities

| Directory | Responsibility |
| --- | --- |
| `apps/storefront` | Catalogue, cart, Cognito login, checkout submission, status polling and order views |
| `apps/store-api` | Validate tokens, enforce ownership, serve catalogue/cart/order APIs, persist checkout requests and dispatch/reconcile queue work |
| `functions/process-checkout` | Consume SQS; invoke payment simulation; atomically update stock and order state; persist outcome events |
| `functions/payment-api` | Simulate approval/rejection with retry-safe checkout identity; no real payments |
| `functions/notifier` | Process outcome events, deduplicate and send SES emails; document delivery crash-window limits |
| `functions/report` | Read sales/stock data and write reports to S3 |
| `contracts` | Shared API and event definitions used by applications, functions and tests |
| `database` | Single authoritative schema migration history, seed data and verification SQL |
| `infra/terraform` | AWS resource definitions, IAM permissions and service integrations |
| `platform` | Kubernetes workloads and Helm add-on configuration |
| `tests` | Cross-component, deployed-system and infrastructure checks |
| `scripts` | Repeatable build, deployment, migration, testing and teardown operations |
| `docs` | Design decisions, operating procedures and report evidence |

## Architecture-to-directory mapping

| Diagram component | Definition / implementation |
| --- | --- |
| VPC, subnets, IGW, NAT and security groups | `infra/terraform/modules/network` |
| EKS cluster and node group | `infra/terraform/modules/eks` |
| API v1/v2 pods, service and HPA | `apps/store-api`, `platform/kubernetes` |
| Pod metrics and node autoscaling | `platform/addons` |
| ALB, target groups and CloudFront routing | `infra/terraform/modules/delivery` |
| Kubernetes-to-ALB target registration | Load Balancer Controller + `target-group-binding.yaml` |
| S3 storefront and images | `delivery` module; assets built from `apps/storefront` |
| Cognito | `identity` module and application authentication code |
| RDS and Secrets Manager | `database` module; schema under top-level `database/` |
| Checkout queue, DLQ and SNS | `messaging` module |
| Four Lambda functions and bindings | `functions` module and top-level `functions/` source |
| EventBridge, report buckets and Athena | `analytics` module; report handler in `functions/report` |
| CloudWatch, alerting and budgets | `observability` module |
| ECR image storage and retention | `registry` module |
| IRSA and scoped execution roles | Owning Terraform modules; API service account in `platform/` |

The reporting Lambda should have a single Terraform owner: the `functions` module owns the function; `analytics` owns its schedule, reporting storage and Athena resources. Pass required IDs/ARNs between modules.

## Resource ownership rules

1. Terraform owns the demo ALB, listeners and target groups in this proposed layout.
2. AWS Load Balancer Controller registers pod targets through TargetGroupBinding. Do not also create an Ingress that provisions another ALB for the same API.
3. Terraform creates AWS IAM roles; Kubernetes service accounts reference the appropriate IRSA role.
4. Kubernetes owns deployments/services/HPA. Helm owns the add-ons installed by the deployment workflow.
5. Cluster Autoscaler changes node desired capacity; configure Terraform ownership/lifecycle deliberately so subsequent applies do not continually reset autoscaler changes.
6. A single migration mechanism runs files from `database/migrations`. Do not independently maintain separate schema histories in Java and Python.
7. Persist dispatch/outcome events transactionally and assign their reconciliation to an explicit application component. A pending row without a retry/reconciliation worker does not provide recovery.

The stable/pilot layout can initially use one service selecting both versions. That does not guarantee an exact traffic percentage. If weighted routing is required, add version-specific services, target groups and bindings and document that deliberate extension.

## Testing organisation

Keep unit tests beside the code they exercise. Keep cross-component tests in the root `tests/` directory.

| Test level | Location | Important coverage |
| --- | --- | --- |
| API unit tests | `apps/store-api/src/test` | Validation, cart totals, ownership logic and checkout rules |
| UI unit/component tests | `apps/storefront/tests` | Rendering, interaction and processing/error states |
| Lambda unit tests | Each function's `tests/` | Event parsing, business decisions, duplicate handling and failure paths |
| Integration | `tests/integration` | Real component interactions, database constraints, event contracts |
| Browser end-to-end | `tests/e2e` | Browse → sign in → cart → checkout → final outcome |
| Correctness | `tests/correctness` | No oversell, one order per checkout, duplicate delivery |
| Security | `tests/security` | Invalid tokens, cross-user access, direct-origin denial |
| Load | `tests/load` | Latency, throughput, queue age and scaling evidence |
| Failure/recovery | `tests/failure` | Retries, DLQ/redrive and commit/publish gap recovery |
| Infrastructure | `tests/infrastructure` | Healthy deployment and private resource configuration |

Record test IDs and requirement IDs in `docs/report/test-plan.md`. Capture actual pass/fail results and evidence in `test-results.md`. Keep large raw outputs outside Git; commit small sanitised summaries where useful.

## Deployment sequence

The scripts are planned automation interfaces; they must be implemented before these commands work.

1. **Prerequisites:** verify AWS account/region, credentials, permissions, quotas and installed tools.
2. **Bootstrap:** create/protect Terraform state infrastructure separately from disposable demo resources.
3. **Infrastructure foundation:** provision networking, ECR, database, identity, EKS, messaging and IAM. Stage resources so image/package references and add-on dependencies exist before use; avoid routine use of Terraform `-target` as the deployment design.
4. **Build:** compile API, build/push container image and package Python functions with compatible dependencies.
5. **Complete integrations:** apply Lambda packages, ALB/CloudFront and reporting/monitoring configuration as dependencies become available.
6. **Workloads:** install add-ons, configure cluster access and deploy Kubernetes manifests with actual image tags and resource outputs.
7. **Database:** run migrations and synthetic seed jobs inside the VPC. Build a dedicated migration image/artifact from the canonical SQL directory if the job needs one.
8. **UI:** supply public runtime/build configuration, build the storefront and publish to S3. Set Cognito callbacks to the CloudFront HTTPS URL and invalidate changed cached entry files when needed.
9. **Verify:** run smoke and end-to-end tests, then bounded load/failure demonstrations.
10. **Evidence and teardown:** capture results and billing evidence; remove disposable resources in dependency-aware order. Remove Kubernetes bindings/controller-managed dependencies while the cluster is still accessible. Verify remaining resources.

## Configuration and generated files

### Commit

- Source code, tests, migration files and synthetic fixtures.
- Terraform `.tf` files and provider dependency lock file (`.terraform.lock.hcl`).
- Dependency lock files and safe `.example` configuration files.
- Kubernetes manifests, Helm values, scripts and sanitised documentation.

### Do not commit

- AWS credentials, tokens, passwords or secret origin header values.
- Terraform state, state backups, saved plans containing sensitive data or `.terraform/` working directories.
- Real `.env`, private `.tfvars` and private backend configuration.
- `node_modules/`, `dist/`, Java `target/`, Python caches and generated Lambda ZIPs.
- Sensitive screenshots/logs or customer information.

Frontend configuration is visible to browsers: only include public values such as region, Cognito client ID, user-pool issuer and API path. Never put secrets in the UI bundle.

Suggested untracked output directories: `build/` for packages, `test-results/` for raw results and `tmp/` for temporary files.

## Minimum first implementation milestone

Build this vertical slice before expanding the entire tree:

- Storefront catalogue and cart screens.
- API catalogue/cart operations with local MySQL.
- Cognito integration and ownership enforcement.
- Checkout acceptance and status contract.
- Checkout worker with atomic stock/order handling and idempotency.
- Terraform demo foundation and one working deployment.
- One end-to-end shopper journey and one concurrent-stock correctness test.

Then add notifications, reporting, pilot deployment, autoscaling, failure recovery and full report evidence. Create directories as their components are implemented; the outline does not require every planned folder to exist on day one.
