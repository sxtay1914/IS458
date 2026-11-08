# FashionStore — Project Directory Structure

Updated 2026-11-08 from all 13 pages of [FashionStore repository guide.pdf](<FashionStore repository guide.pdf>) and checked against the current local files. This replaces the original proposed tree with the implemented layout. The PDF is a dated reference; this document and the [repository guide](fashionstore/docs/repository-guide.md) record corrections and current repository context.

The Git repository is [sxtay1914/IS458](https://github.com/sxtay1914/IS458). The application lives in its `fashionstore/` subdirectory. Paths below are relative to that application directory unless stated otherwise. Run all `make` commands from `fashionstore/` (or use `make -C fashionstore ...` from the repository root).

Scope remains the Part B demo on AWS Singapore (`ap-southeast-1`), with a US$100 alert budget. The complete demo was restarted with the supplied UI/images, tested and torn down on 2026-11-07. The website is removed. The original five-day runtime and leave-running-for-review instructions are superseded. Part A production architecture is documentation only.

## Technology and recorded status

| Area | Implemented choice | Recorded verification through 2026-11-08 |
| --- | --- | --- |
| Storefront | React 19, TypeScript, Vite, self-hosted Nunito; supplied UI integrated | 21 unit tests, typecheck and production build passed |
| Store API | Spring Boot 3.5, Java 21; EKS | 27 MySQL 8.4 integration tests passed after the local cart fix; prior amd64 build was deployed |
| Functions | Four Python 3.12 arm64 Lambdas | 57 pytest tests against local MySQL 8.4; live checkout and report processing passed |
| Database | RDS MySQL 8.4; Flyway canonical SQL migrations | V001–V003 migrated on RDS with verified TLS; demo inventory seeded |
| Infrastructure | Terraform; ten service modules plus private-bucket helper | 33 mock-provider test runs; AWS demo applied with two Free-plan-eligible t3.small workers |
| Workloads | Kubernetes, Kustomize and Helm | Two v1 pods and one v2 pod became ready; app and three add-ons subsequently removed for teardown |
| Browser tests | Playwright | Four mock journeys passed; restarted demo: two passed, one failed on a cart database deadlock, one intentionally skipped |
| Live API checks | pytest | Restarted demo: 31 passed, four optional chaos/slow tests skipped |
| Reporting | Lambda, S3 and Athena | Sales and stock CSVs generated; daily revenue query succeeded |

The supplied UI was deployed with its checkout retry fix preserved. All nine supplied image URLs returned HTTP 200 and matched their source hashes; ten product images loaded with no mobile horizontal overflow. [Restart evidence](fashionstore/docs/report/evidence/2026-11-07-restart/results.json) records that deployment's checks and failed browser purchase; [first-demo evidence](fashionstore/docs/report/evidence/2026-11-06/results.json) remains historical. The cart deadlock was fixed and retested locally on 2026-11-08: [fix evidence](fashionstore/docs/report/evidence/2026-11-08-cart-deadlock/results.json) records the failing baseline and 27 passing API tests. Post-fix AWS/browser testing remains pending, so the successful-release `v0.1.0` tag is withheld. [Teardown verification](fashionstore/docs/report/evidence/2026-11-07-restart/teardown.json) confirms empty demo Terraform state and 23 checks with zero remaining resources or errors. The budget/state/GitHub OIDC bootstrap is retained.

Separate non-demo resources remain: three stopped Assignment3 EC2 instances, three 8 GB gp3 volumes and one unattached Elastic IP. The volumes and Elastic IP can still incur charges; demo cleanup does not establish zero account spending.

## Repository boundary

```text
IS458/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── terraform-plan.yml
├── README.md
├── LICENSE
├── FashionStore repository guide.pdf
├── FashionStore_Project_Directory_Structure.md
└── fashionstore/                       # application root shown below
```

## Current source tree

This lists the current source/configuration files, including local uncommitted files. Generated artifacts, installed dependencies, state, secrets and caches are excluded. Directories in the old proposal that have not been implemented are listed separately below.

```text
└── fashionstore/
    ├── apps/
    │   ├── store-api/
    │   │   ├── .mvn/
    │   │   │   └── wrapper/
    │   │   │       └── maven-wrapper.properties
    │   │   ├── src/
    │   │   │   ├── main/
    │   │   │   │   ├── java/
    │   │   │   │   │   └── com/
    │   │   │   │   │       └── fashionstore/
    │   │   │   │   │           ├── auth/
    │   │   │   │   │           │   ├── CognitoAccessTokenValidator.java
    │   │   │   │   │           │   ├── CurrentUser.java
    │   │   │   │   │           │   └── UserEmailResolver.java
    │   │   │   │   │           ├── cart/
    │   │   │   │   │           │   ├── CartController.java
    │   │   │   │   │           │   ├── CartRepository.java
    │   │   │   │   │           │   └── LineItem.java
    │   │   │   │   │           ├── catalog/
    │   │   │   │   │           │   ├── CatalogController.java
    │   │   │   │   │           │   ├── CatalogRepository.java
    │   │   │   │   │           │   └── Product.java
    │   │   │   │   │           ├── checkout/
    │   │   │   │   │           │   ├── CheckoutController.java
    │   │   │   │   │           │   ├── CheckoutRepository.java
    │   │   │   │   │           │   ├── CheckoutService.java
    │   │   │   │   │           │   └── CheckoutStatus.java
    │   │   │   │   │           ├── common/
    │   │   │   │   │           │   ├── ApiException.java
    │   │   │   │   │           │   ├── CorrelationIdFilter.java
    │   │   │   │   │           │   ├── ErrorHandler.java
    │   │   │   │   │           │   └── VersionController.java
    │   │   │   │   │           ├── configuration/
    │   │   │   │   │           │   ├── AppProperties.java
    │   │   │   │   │           │   ├── AwsConfig.java
    │   │   │   │   │           │   ├── DataSourceConfig.java
    │   │   │   │   │           │   └── SecurityConfig.java
    │   │   │   │   │           ├── messaging/
    │   │   │   │   │           │   ├── CheckoutQueue.java
    │   │   │   │   │           │   ├── InMemoryMessaging.java
    │   │   │   │   │           │   ├── OutcomePublisher.java
    │   │   │   │   │           │   ├── Reconciler.java
    │   │   │   │   │           │   ├── SnsOutcomePublisher.java
    │   │   │   │   │           │   └── SqsCheckoutQueue.java
    │   │   │   │   │           ├── orders/
    │   │   │   │   │           │   ├── Order.java
    │   │   │   │   │           │   ├── OrdersController.java
    │   │   │   │   │           │   └── OrdersRepository.java
    │   │   │   │   │           └── StoreApiApplication.java
    │   │   │   │   └── resources/
    │   │   │   │       ├── application-local.yml
    │   │   │   │       └── application.yml
    │   │   │   └── test/
    │   │   │       ├── java/
    │   │   │       │   └── com/
    │   │   │       │       └── fashionstore/
    │   │   │       │           ├── AbstractIntegrationTest.java
    │   │   │       │           ├── CartApiTest.java
    │   │   │       │           ├── CartConcurrencyTest.java
    │   │   │       │           ├── CatalogApiTest.java
    │   │   │       │           ├── CheckoutApiTest.java
    │   │   │       │           ├── OrdersAndReconcilerTest.java
    │   │   │       │           └── SecurityTest.java
    │   │   │       └── resources/
    │   │   │           └── docker-java.properties
    │   │   ├── .dockerignore
    │   │   ├── Dockerfile
    │   │   ├── README.md
    │   │   ├── mvnw
    │   │   ├── mvnw.cmd
    │   │   └── pom.xml
    │   └── storefront/
    │       ├── public/
    │       │   ├── images/
    │       │   │   ├── bag-001.svg
    │       │   │   ├── btm-001.svg
    │       │   │   ├── btm-002.svg
    │       │   │   ├── drs-001.svg
    │       │   │   ├── drs-002.svg
    │       │   │   ├── flash-001.svg
    │       │   │   ├── sho-001.svg
    │       │   │   ├── top-001.svg
    │       │   │   └── top-002.svg
    │       │   └── config.json
    │       ├── src/
    │       │   ├── api/
    │       │   │   ├── ApiContext.tsx
    │       │   │   ├── client.ts
    │       │   │   └── index.ts
    │       │   ├── auth/
    │       │   │   ├── AuthContext.tsx
    │       │   │   └── pkce.ts
    │       │   ├── components/
    │       │   │   ├── CartItem.tsx
    │       │   │   ├── CheckoutStatus.tsx
    │       │   │   ├── CheckoutSteps.tsx
    │       │   │   ├── Footer.tsx
    │       │   │   ├── Icon.tsx
    │       │   │   ├── Navigation.tsx
    │       │   │   ├── NotFound.tsx
    │       │   │   └── ProductCard.tsx
    │       │   ├── hooks/
    │       │   │   ├── useCart.ts
    │       │   │   └── useCheckoutPolling.ts
    │       │   ├── pages/
    │       │   │   ├── AuthCallbackPage.tsx
    │       │   │   ├── CartPage.tsx
    │       │   │   ├── CheckoutPage.tsx
    │       │   │   ├── CheckoutStatusPage.tsx
    │       │   │   ├── OrderDetailsPage.tsx
    │       │   │   ├── OrdersPage.tsx
    │       │   │   ├── ProductDetailsPage.tsx
    │       │   │   ├── ProductsPage.tsx
    │       │   │   └── checkoutKey.ts
    │       │   ├── styles/
    │       │   │   └── app.css
    │       │   ├── types/
    │       │   │   └── index.ts
    │       │   ├── App.tsx
    │       │   ├── config.ts
    │       │   └── main.tsx
    │       ├── tests/
    │       │   ├── checkout.test.tsx
    │       │   ├── client.test.ts
    │       │   ├── components.test.tsx
    │       │   ├── contract.test.ts
    │       │   ├── helpers.tsx
    │       │   ├── pkce.test.ts
    │       │   ├── polling.test.tsx
    │       │   ├── setup.ts
    │       │   └── storefront.test.tsx
    │       ├── .env.example
    │       ├── README.md
    │       ├── index.html
    │       ├── package-lock.json
    │       ├── package.json
    │       ├── tsconfig.json
    │       └── vite.config.ts
    ├── contracts/
    │   ├── events/
    │   │   ├── checkout-request.schema.json
    │   │   └── checkout-status.schema.json
    │   ├── examples/
    │   │   ├── checkout-confirmed.json
    │   │   ├── checkout-rejected.json
    │   │   └── checkout-request.json
    │   ├── README.md
    │   └── openapi.yaml
    ├── database/
    │   ├── migrations/
    │   │   ├── V001__catalog_and_cart.sql
    │   │   ├── V002__checkout_and_orders.sql
    │   │   └── V003__dispatch_and_notification.sql
    │   ├── queries/
    │   │   ├── verify-idempotency.sql
    │   │   ├── verify-report-totals.sql
    │   │   └── verify-stock.sql
    │   ├── seeds/
    │   │   ├── inventory.sql
    │   │   └── products.sql
    │   └── README.md
    ├── docs/
    │   ├── report/
    │   │   └── evidence/
    │   │       ├── 2026-11-06/
    │   │       │   ├── new-ui-desktop.png
    │   │       │   ├── new-ui-mobile.png
    │   │       │   └── results.json
    │   │       ├── 2026-11-07-restart/
    │   │       │   ├── desktop.png
    │   │       │   ├── mobile.png
    │   │       │   ├── results.json
    │   │       │   └── teardown.json
    │   │       └── 2026-11-08-cart-deadlock/
    │   │           └── results.json
    │   ├── implementation-plan.md
    │   └── repository-guide.md
    ├── functions/
    │   ├── common/
    │   │   └── fashionstore_common/
    │   │       ├── __init__.py
    │   │       ├── db.py
    │   │       ├── rds-ca.pem
    │   │       └── testing.py
    │   ├── notifier/
    │   │   ├── templates/
    │   │   │   ├── confirmed.html
    │   │   │   └── rejected.html
    │   │   ├── tests/
    │   │   │   ├── conftest.py
    │   │   │   └── test_notifier.py
    │   │   ├── handler.py
    │   │   ├── repository.py
    │   │   └── requirements.txt
    │   ├── payment-api/
    │   │   ├── tests/
    │   │   │   ├── conftest.py
    │   │   │   └── test_payment.py
    │   │   ├── handler.py
    │   │   └── requirements.txt
    │   ├── process-checkout/
    │   │   ├── tests/
    │   │   │   ├── conftest.py
    │   │   │   ├── fakes.py
    │   │   │   ├── test_checkout_db.py
    │   │   │   ├── test_contracts.py
    │   │   │   ├── test_db_connection.py
    │   │   │   └── test_validation.py
    │   │   ├── handler.py
    │   │   ├── repository.py
    │   │   ├── requirements.txt
    │   │   └── service.py
    │   ├── report/
    │   │   ├── queries/
    │   │   │   ├── sales.sql
    │   │   │   └── stock.sql
    │   │   ├── tests/
    │   │   │   ├── conftest.py
    │   │   │   └── test_report.py
    │   │   ├── handler.py
    │   │   └── requirements.txt
    │   ├── README.md
    │   └── requirements-dev.txt
    ├── infra/
    │   └── terraform/
    │       ├── bootstrap/
    │       │   ├── tests/
    │       │   │   ├── bootstrap.tftest.hcl
    │       │   │   └── plan_state_access.tftest.hcl
    │       │   ├── .terraform.lock.hcl
    │       │   ├── main.tf
    │       │   ├── outputs.tf
    │       │   ├── terraform.tfvars.example
    │       │   ├── variables.tf
    │       │   └── versions.tf
    │       ├── environments/
    │       │   └── demo/
    │       │       ├── tests/
    │       │       │   └── stack.tftest.hcl
    │       │       ├── .terraform.lock.hcl
    │       │       ├── backend.hcl.example
    │       │       ├── main.tf
    │       │       ├── outputs.tf
    │       │       ├── providers.tf
    │       │       ├── terraform.tfvars.example
    │       │       ├── variables.tf
    │       │       └── versions.tf
    │       ├── modules/
    │       │   ├── analytics/
    │       │   │   ├── tests/
    │       │   │   │   └── analytics.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── database/
    │       │   │   ├── tests/
    │       │   │   │   └── database.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── delivery/
    │       │   │   ├── tests/
    │       │   │   │   └── delivery.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── spa-rewrite.js
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── eks/
    │       │   │   ├── tests/
    │       │   │   │   └── eks.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── functions/
    │       │   │   ├── tests/
    │       │   │   │   └── functions.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── identity/
    │       │   │   ├── tests/
    │       │   │   │   └── identity.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── messaging/
    │       │   │   ├── tests/
    │       │   │   │   └── messaging.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── network/
    │       │   │   ├── tests/
    │       │   │   │   └── network.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── observability/
    │       │   │   ├── tests/
    │       │   │   │   └── observability.tftest.hcl
    │       │   │   ├── .terraform.lock.hcl
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   ├── private-bucket/
    │       │   │   ├── main.tf
    │       │   │   ├── outputs.tf
    │       │   │   ├── variables.tf
    │       │   │   └── versions.tf
    │       │   └── registry/
    │       │       ├── tests/
    │       │       │   └── registry.tftest.hcl
    │       │       ├── .terraform.lock.hcl
    │       │       ├── main.tf
    │       │       ├── outputs.tf
    │       │       ├── variables.tf
    │       │       └── versions.tf
    │       ├── tests/
    │       │   └── mocks/
    │       │       └── aws.tfmock.hcl
    │       └── README.md
    ├── platform/
    │   ├── addons/
    │   │   ├── aws-load-balancer-controller/
    │   │   │   └── values.yaml
    │   │   ├── cluster-autoscaler/
    │   │   │   └── values.yaml
    │   │   └── metrics-server/
    │   │       └── values.yaml
    │   └── kubernetes/
    │       ├── base/
    │       │   ├── configmap.yaml
    │       │   ├── deployment-v1.yaml
    │       │   ├── deployment-v2.yaml
    │       │   ├── hpa-v1.yaml
    │       │   ├── kustomization.yaml
    │       │   ├── namespace.yaml
    │       │   ├── service-account.yaml
    │       │   ├── service.yaml
    │       │   └── target-group-binding.yaml
    │       ├── jobs/
    │       │   ├── database-migration.yaml
    │       │   └── seed-demo.yaml
    │       └── overlays/
    │           └── demo/
    │               ├── generated/
    │               │   └── .gitignore
    │               ├── configmap-patch.yaml
    │               ├── kustomization.yaml
    │               └── resource-limits-patch.yaml
    ├── scripts/
    │   ├── build-push-api.sh
    │   ├── create-test-users.sh
    │   ├── deploy-storefront.sh
    │   ├── package-functions.sh
    │   ├── render-k8s-config.sh
    │   └── select-kinds.py
    ├── tests/
    │   ├── correctness/
    │   │   └── test_checkout_live.py
    │   ├── e2e/
    │   │   ├── specs/
    │   │   │   ├── rejected-checkout.spec.ts
    │   │   │   └── shopper-journey.spec.ts
    │   │   ├── support/
    │   │   │   ├── env.ts
    │   │   │   ├── mock-backend.ts
    │   │   │   └── session.ts
    │   │   ├── tools/
    │   │   │   └── get-token.mjs
    │   │   ├── .gitignore
    │   │   ├── package-lock.json
    │   │   ├── package.json
    │   │   ├── playwright.config.ts
    │   │   └── tsconfig.json
    │   ├── failure/
    │   │   ├── test_dispatch_recovery.py
    │   │   ├── test_dlq_redrive.py
    │   │   ├── test_notification_recovery.py
    │   │   └── test_worker_retry.py
    │   ├── infrastructure/
    │   │   ├── smoke-test.sh
    │   │   └── verify-private-resources.sh
    │   ├── load/
    │   │   ├── lib/
    │   │   │   └── common.js
    │   │   ├── profiles/
    │   │   │   ├── demo.json
    │   │   │   └── smoke.json
    │   │   ├── .gitignore
    │   │   ├── browse.js
    │   │   ├── checkout.js
    │   │   ├── flash-sale.js
    │   │   └── make-tokens.sh
    │   ├── security/
    │   │   ├── test_authentication.py
    │   │   ├── test_origin_access.py
    │   │   └── test_ownership.py
    │   ├── README.md
    │   ├── conftest.py
    │   ├── pytest.ini
    │   └── requirements-live.txt
    ├── .gitignore
    ├── Makefile
    └── README.md
```

## Component responsibilities and ownership

| Directory | Responsibility |
| --- | --- |
| `apps/storefront` | Catalogue, server-side cart, Cognito hosted-UI sign-in with PKCE, checkout submission/status polling and shopper order views |
| `apps/store-api` | Validate Cognito access tokens and API scopes, enforce ownership, persist PENDING checkout and clear the cart transactionally, send SQS work and reconcile missed sends/publications |
| `functions/process-checkout` | Validate messages, read prices from MySQL, invoke deterministic payment simulation, atomically write orders/items and conditionally decrement stock; publish stored outcomes |
| `functions/payment-api` | Retry-safe simulated payment; no real payments; supports deliberate declines |
| `functions/notifier` | SNS outcomes to SES with a unique notification row and lease; duplicate/concurrent delivery is deduplicated, but a crash after SES accepts mail and before SENT is saved can cause duplicate email on retry |
| `functions/report` | Sales and stock CSVs partitioned by date for Athena |
| `functions/common` | Shared MySQL/Secrets Manager connection handling and test database setup; copied into Lambda packages |
| `contracts` | OpenAPI, versioned SQS/SNS JSON schemas and example messages |
| `database` | Flyway migration history, synthetic seeds and evidence SQL; migration and seed Jobs reach isolated RDS through EKS |
| `infra/terraform` | AWS resources, IAM and service bindings; persistent bootstrap state separate from disposable demo state |
| `platform` | Versioned Kubernetes deployments, services, TargetGroupBindings, HPA/disruption budget, database Jobs and Helm values |
| `scripts` | Six implemented packaging, configuration, image, storefront and test-user helpers; Makefile supplies deployment orchestration |
| `tests` | Browser, live security/correctness/recovery, infrastructure and k6 checks; unit/component tests stay beside their source |
| `docs` | Repository guide, implementation plan and deployment screenshots/results; full report and runbook remain future work |

### AWS-to-directory mapping

| Component | Owner |
| --- | --- |
| VPC, two-AZ subnet layers, one NAT, S3 gateway endpoint and security groups | `infra/terraform/modules/network` |
| ECR image registry and retention | `modules/registry` under `infra/terraform` |
| RDS and managed database secret | `modules/database`; SQL history remains in top-level `database/` |
| EKS, managed nodes, OIDC/access and IRSA | `modules/eks`; Helm add-ons in `platform/addons` |
| Internal ALB, weighted v1/v2 target groups, private storefront bucket, OAC, CloudFront VPC origin and SPA rewrite | `modules/delivery` |
| Pod registration into Terraform target groups | Two services and two TargetGroupBindings in `platform/kubernetes/base`; AWS Load Balancer Controller registers targets only |
| Cognito pool, hosted UI, public PKCE client and API scopes | `modules/identity`; token validation in API, PKCE/session handling in UI |
| Checkout SQS, checkout DLQ, notifier-failures queue, outcome/operations SNS topics | `modules/messaging` |
| Four Lambdas, execution roles, event bindings, report schedule and SES identities | `modules/functions` |
| Reports/results buckets, Athena workgroup, Glue tables and named queries | `modules/analytics` |
| CloudWatch alarms and dashboard | `modules/observability`; persistent budget alerts in `bootstrap` |
| Reusable private, encrypted, TLS-only buckets | `modules/private-bucket` helper |

`modules/` in the table means `infra/terraform/modules/`. Ten service modules plus the bucket helper means eleven module directories. Each service module has `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` and mocked tests; the helper has no separate test directory.

### Resource and correctness rules

1. Terraform owns the ALB, listener rule and two target groups. Kubernetes owns two version-specific services and bindings; do not add an Ingress that creates a second ALB.
2. The listener weights, initially 90/10, set pilot traffic. Pod counts (v1 two, v2 one) do not define that split. HPA scales v1; Cluster Autoscaler controls node desired capacity, which Terraform ignores.
3. Terraform creates IAM roles; service accounts reference IRSA. Helm installs metrics-server, Cluster Autoscaler and AWS Load Balancer Controller.
4. Flyway alone runs `database/migrations`; avoid independent Java/Python schema histories.
5. `orders.checkout_id` and `notification_log.checkout_id` are unique. Conditional stock updates and one transaction prevent negative inventory and partial multi-item orders; the API reconciler uses `SKIP LOCKED` for missed SQS dispatch and SNS publication.
6. The storefront polls the API, which reads status from MySQL. SNS sends outcomes to the notifier; it does not push status into the API.
7. Notification-log uniqueness proves one database row, not exactly one SES delivery. A send/SENT-update crash window remains; `attempts > 1` flags retries and possible duplicates, not confirmed duplicate delivery or a fixed upper bound.
8. Cognito sign-in uses authorization code plus PKCE. `USER_PASSWORD_AUTH` is not used because those tokens lack the custom API scopes. Browser runtime configuration in `public/config.json` contains public values only.

## Tests and commands

| Level | Location | Command from `fashionstore/` |
| --- | --- | --- |
| Terraform formatting/validation | `infra/terraform` | `make validate` |
| Mocked Terraform tests | Service modules, bootstrap and demo `tests/`; shared `tests/mocks` | `make tf-test` |
| Lambda unit/integration | `functions/*/tests` | `make py-test` (local MySQL required) |
| API integration | `apps/store-api/src/test` | `make api-test` (Docker required) |
| UI unit/type/build | `apps/storefront/tests` | `make web-test` |
| Mocked browser journeys | `tests/e2e/specs`, `support` | `make e2e` |
| Live security, correctness and recovery | `tests/security`, `correctness`, `failure` | `make live-test` with configured test users/tokens |
| Live browser journeys | `tests/e2e` | `make e2e-live` |
| Infrastructure | `tests/infrastructure` | `make smoke`, `make verify-private` |
| Load/flash sale | `tests/load` | `make load-browse load-checkout load-flash PROFILE=smoke` |

`make help` is the command index; `make test` runs the offline suites. Install the required tools/dependencies and start/migrate local MySQL first; see [tests/README.md](fashionstore/tests/README.md). Live pytest skips without `FS_BASE_URL`; chaos and slow checks additionally require `FS_ALLOW_CHAOS=1` and `FS_RUN_SLOW=1`. Run disruptive tests one at a time. Reseed `FLASH-001` before each flash-sale run.

## Deployment sequence and remaining work

The Makefile and six scripts exist; these commands were exercised during the first AWS demo and the restart with the supplied UI/images. Restart testing and verified demo teardown are complete. The cart fix passed local regression tests; the failed purchase journey still needs a post-fix live browser run.

1. From the repository root, `cd fashionstore`. Configure bootstrap for `github_repository = "sxtay1914/IS458"`, alert recipients and the intended AWS account/region. Run `make bootstrap`; preserve its local state securely outside Git. Set GitHub repository variables `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET` from the bootstrap outputs.
2. Copy/fill `backend.hcl` and `terraform.tfvars` in `infra/terraform/environments/demo` using their examples. Set owner, expiry, SES addresses, EKS admin ARNs and allowed public endpoint CIDRs. Run `make init-demo deploy-demo`; the plan target packages the Lambdas first.
3. Verify SES sender and recipient addresses. Run `make k8s-config addons db-migrate-remote db-seed-remote`. EKS is needed before the application deployment so its Jobs can reach isolated RDS. Run `SMOKE_EMAIL=<verified-address> make smoke`.
4. Build/push distinct API tags: `make push-api TAG=v1` and `make push-api TAG=v2`; then `make k8s-config V1_TAG=v1 V2_TAG=v2 k8s-apply`. The amd64 image build and v1/v2 rollout passed during the first demo.
5. Run `make deploy-storefront verify-private`. If the VPC origin fails, investigate the documented CloudFront service-managed security-group input before proceeding.
6. Create verified test shoppers with `make test-users`, configure the `FS_*`/`E2E_*` variables in the test README and run `make live-test e2e-live`. Hosted-UI PKCE automation passed during the first demo.
7. Run bounded chaos, load and pilot-weight demonstrations, manually invoke the report with `{"date":"today"}`, run Athena queries and collect evidence and billing data.
8. After testing, export evidence and follow the plan's staged manual teardown checklist, retaining Lambda execution permissions until its ENIs are released. `make destroy-demo` removes bindings, uninstalls add-ons and runs one full Terraform destroy; it does not implement the staged sequence. Check residual resources and charges; retain bootstrap only while its state is still needed, then remove it last. RDS uses no final snapshot: export any needed data first.

### CI in the current monorepo

Workflow definitions are at the Git repository root's `.github/workflows/`, where GitHub discovers them after they are pushed. Shell steps default to `fashionstore/`; explicit working directories, dependency caches and artifact paths use repository-relative paths. The Terraform plan workflow watches the application infrastructure/functions, packaging script, Makefile and its own workflow file. It requires `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET`; GitHub CI passed all six jobs on the pushed UI/image build.

The CI definition checks/builds; it does not push ECR images or deploy Kubernetes. The plan definition runs a Terraform plan when configured; it does not post a PR comment. Bootstrap creates an apply role, but no CD workflow is implemented. Deployments currently use manual `make` commands.

## Planned documentation, not current source

The original outline's `local/`, `docs/architecture/`, `docs/runbooks/`, `docs/demo/` and root `tests/integration/`/`fixtures/` directories are not present. Do not treat them as completed deliverables. Local MySQL currently uses Makefile targets, not Docker Compose; integration tests live with the API and functions. Add report structure, requirement/test traceability, architecture assets, runbooks, cost records and curated evidence when that work is performed. Deployment screenshots and sanitized results now exist in `docs/report/evidence/2026-11-06/` and `2026-11-07-restart/`; the full submission report is still outstanding.

The old proposed scripts (such as `deploy-demo.sh`, `provision-infra.sh` and `collect-evidence.sh`) are not current interfaces. Use the Makefile targets and the six real scripts in the tree. No deployment workflow or separate per-function READMEs are present.

## Configuration and generated files

Commit source, tests, migrations, synthetic fixtures, safe examples, manifests, Helm values, scripts, documentation, npm lock files and Terraform provider lock files when generated. Keep AWS credentials, passwords, real environment/backend/tfvars files, Terraform state/plans, `.terraform/`, package ZIPs, installed dependencies, caches, tokens and sensitive evidence out of Git.

Generated Lambda packages go in `build/functions/`; generated Kubernetes configuration goes in `platform/kubernetes/overlays/demo/generated/*.env`; UI output goes in `apps/storefront/dist/`. The source `public/config.json` is a placeholder that deployment replaces in the published build. Frontend configuration is visible to browsers and must never contain secrets.
