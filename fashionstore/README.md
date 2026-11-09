# FashionStore (IS458, Part B)

Implementation architecture for FashionStore on AWS Singapore (`ap-southeast-1`).
Terraform provisions AWS; Kubernetes, Kustomize and Helm configure EKS workloads.

* Current directory tree and repository boundaries: [Project Directory Structure](../FashionStore_Project_Directory_Structure.md)
* Plan, decisions, who-does-what, teardown: [docs/implementation-plan.md](docs/implementation-plan.md)
* What every folder and file is for: [docs/repository-guide.md](docs/repository-guide.md)
* Infrastructure: [infra/terraform/README.md](infra/terraform/README.md)
* Contracts between the halves: [contracts/README.md](contracts/README.md)
* Tests: [tests/README.md](tests/README.md)
* Local test dashboard: [dashboard/README.md](dashboard/README.md)
* Presentation outline: [docs/presentation-content-structure.md](docs/presentation-content-structure.md)

Run commands below from `fashionstore/` (`cd fashionstore` from the IS458 Git root). Workflow definitions live at the Git root in `../.github/workflows/`, with working directories and paths configured for this application. Previous builds passed all six CI jobs; new-commit CI results are not yet recorded here. The AWS plan job requires `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET`. Deploys use manual Makefile commands; no CD workflow exists.

## What is in the repo now

| Area | Status |
| --- | --- |
| `infra/terraform` (bootstrap + 10 service modules + bucket helper + demo env) | Built; 33 `terraform test` runs green (mocked AWS) |
| `database` (Flyway V001–V003, seeds, verify queries) | Migrated RDS MySQL 8.4 with verified TLS |
| `functions` (process-checkout, payment-api, notifier, report) | Built; 57 pytest tests green against real MySQL |
| `contracts` (OpenAPI, event schemas, examples) | Built; validated in Lambda and store-api tests |
| `platform` (Kustomize base/overlay, Flyway + seed Jobs, Helm values) | Active November 10 demo: two Ready EKS workers; V001–V003 and seed Jobs completed |
| `apps/store-api` (Spring Boot 3.5, Java 21) | 27 local MySQL 8.4 tests passed; deployed image `demo-20261109-49cc9e8` includes the cart fix |
| `apps/storefront` (React 19, Vite) | 21 unit tests, typecheck and production build passed |
| `tests/e2e` (Playwright) | November 10: 3 live journeys passed, including the previously failing purchase; 1 fault-injection journey skipped |
| `tests/security`, `correctness`, `failure` (pytest), `tests/load` (k6) | November 10: 31 live API tests and 7 private-access checks passed; 4 optional tests skipped; no sustained load run at handoff |
| `dashboard` (Streamlit) | 112 offline tests passed; both tabs rendered without browser errors; live dashboard drills not run |

The November 10 demo is running for owner testing: [storefront](https://d33zy72vrkzz7v.cloudfront.net) and [local dashboard](http://localhost:8501). [Current evidence](docs/report/evidence/2026-11-10-restart/results.json) records the successful live cart purchase, API/browser checks and a Terraform plan with no changes. Verified demo release: [`v0.1.0`](https://github.com/sxtay1914/IS458/tree/v0.1.0). The [November 7 teardown](docs/report/evidence/2026-11-07-restart/teardown.json), [earlier browser failure](docs/report/evidence/2026-11-07-restart/results.json) and [November 8 local fix](docs/report/evidence/2026-11-08-cart-deadlock/results.json) remain historical evidence.

The November 7 inventory recorded three stopped Assignment3 EC2 instances, three 8 GB gp3 volumes and one unattached Elastic IP outside the demo. That is a dated inventory, not a fresh account-wide check.

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
# Leave running for owner testing; afterwards export evidence and follow:
# docs/implementation-plan.md#teardown-rules-manual-destroy
```

Keep AWS and the local dashboard running for the owner's tests, then remind the owner to tear down. There is no automatic shutdown or five-day runtime. Afterwards follow the staged checklist in the plan so Lambda execution permissions remain available until its network interfaces are released. `make destroy-demo` runs one full destroy and does not implement that staged sequence. The US$100 budget sends alerts and does not stop spending. The preflight billing snapshot showed about US$6.30 usage for November 1–9, offset by credits; it is delayed data, not a verified remaining-credit balance or final demo cost.
