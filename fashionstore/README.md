# FashionStore (IS458, Part B)

Implementation architecture for FashionStore on AWS Singapore (`ap-southeast-1`).
Terraform provisions AWS; Kubernetes, Kustomize and Helm configure EKS workloads.

* Current directory tree and repository boundaries: [Project Directory Structure](../FashionStore_Project_Directory_Structure.md)
* Plan, decisions, who-does-what, teardown: [docs/implementation-plan.md](docs/implementation-plan.md)
* What every folder and file is for: [docs/repository-guide.md](docs/repository-guide.md)
* Infrastructure: [infra/terraform/README.md](infra/terraform/README.md)
* Contracts between the halves: [contracts/README.md](contracts/README.md)
* Tests: [tests/README.md](tests/README.md)

Run commands below from `fashionstore/` (`cd fashionstore` from the IS458 Git root). Workflow definitions live at the Git root in `../.github/workflows/`, with working directories and paths configured for this application. They are pushed and CI passed all six jobs; the AWS plan job also requires `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET`. Deploys use manual Makefile commands; no CD workflow exists.

## What is in the repo now

| Area | Status |
| --- | --- |
| `infra/terraform` (bootstrap + 10 service modules + bucket helper + demo env) | Built; 33 `terraform test` runs green (mocked AWS) |
| `database` (Flyway V001–V003, seeds, verify queries) | Migrated RDS MySQL 8.4 with verified TLS |
| `functions` (process-checkout, payment-api, notifier, report) | Built; 57 pytest tests green against real MySQL |
| `contracts` (OpenAPI, event schemas, examples) | Built; validated in Lambda and store-api tests |
| `platform` (Kustomize base/overlay, Flyway + seed Jobs, Helm values) | EKS deployment, migration and seed Jobs verified; demo infrastructure subsequently removed |
| `apps/store-api` (Spring Boot 3.5, Java 21) | 24 MySQL 8.4 integration tests passed; amd64 image built and deployed |
| `apps/storefront` (React 19, Vite) | 21 unit tests, typecheck and production build passed |
| `tests/e2e` (Playwright) | 4 mocked journeys passed; restarted demo: 2 passed, 1 failed on a cart database deadlock, 1 intentionally skipped |
| `tests/security`, `correctness`, `failure` (pytest), `tests/load` (k6) | Restarted demo: 31 live API tests passed, 4 optional chaos/slow tests skipped; k6 runs remain outstanding |

The demo was torn down on 2026-11-07 and the website is removed. [Teardown verification](docs/report/evidence/2026-11-07-restart/teardown.json) confirms empty demo Terraform state and 23 checks with zero remaining resources or errors. Bootstrap remains (state bucket, GitHub OIDC roles and budget alerts). [Restart evidence](docs/report/evidence/2026-11-07-restart/results.json) records the supplied UI/image checks and the browser failure. The cart deadlock remains unfixed, so the successful-release `v0.1.0` tag is withheld. [First-demo results](docs/report/evidence/2026-11-06/results.json) remain historical evidence.

Separate non-demo resources remain: three stopped Assignment3 EC2 instances, three 8 GB gp3 volumes and one unattached Elastic IP. Storage and Elastic IP charges may continue.

## Tests that run without AWS

```bash
make db-local-up db-migrate          # MySQL 8 + Flyway in Docker
pip install -r functions/requirements-dev.txt
make test                            # terraform + pytest + store-api + storefront + e2e
```

## Deploy (short demo session)

```bash
make bootstrap                       # once; then copy backend.hcl + terraform.tfvars
make init-demo deploy-demo           # ~20-25 min
make k8s-config addons               # kubeconfig, metrics-server, CA, LB controller
make db-migrate-remote db-seed-remote
SMOKE_EMAIL=you@verified.example make smoke
make push-api TAG=v1 && make push-api TAG=v2
make k8s-config V1_TAG=v1 V2_TAG=v2 && make k8s-apply
make deploy-storefront
make verify-private
make test-users EMAILS="a@you b@you a+decline@you" TEST_USER_PASSWORD=...
make live-test e2e-live              # with the FS_* / E2E_* variables in tests/README.md
make load-browse load-checkout load-flash PROFILE=demo
# After tests, export evidence and follow the staged teardown checklist:
# docs/implementation-plan.md#teardown-rules-manual-destroy
```

The latest instruction is to tear down after testing; there is no automatic shutdown or five-day runtime. Follow the staged checklist in the plan so Lambda execution permissions remain available until its network interfaces are released. `make destroy-demo` performs a single full Terraform destroy and does not implement that staged sequence. The US$100 budget sends alerts and does not automatically stop spending.
