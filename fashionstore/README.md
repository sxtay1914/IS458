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
| `platform` (Kustomize base/overlay, Flyway + seed Jobs, Helm values) | 13:55 rebuild: two Ready workers, three available add-ons and both API rollouts complete; no migration or seed Jobs run |
| `apps/store-api` (Spring Boot 3.5, Java 21) | 27 local MySQL 8.4 tests passed; deployed image `demo-20261109-49cc9e8` includes the cart fix |
| `apps/storefront` (React 19, Vite) | 21 unit tests, typecheck and production build passed |
| `tests/e2e` (Playwright) | Earlier November 10 00:37 run: 3 live passes/1 skip; not rerun for the 13:55 rebuild |
| `tests/security`, `correctness`, `failure` (pytest), `tests/load` (k6) | Earlier 00:37 run: 31 API passes/4 skips and 7 private-access passes; no tests run for this rebuild |
| `dashboard` (Streamlit) | Server restarted at 13:55; earlier 112 offline passes/two tab renders are historical, not current retests |

Setup completed on November 10 at 13:55 (UTC+8): [storefront](https://d1oj35ccg258u3.cloudfront.net) and [local dashboard](http://localhost:8501). [Redeployment evidence](docs/report/evidence/2026-11-10-restart/redeploy.json) records 63 Terraform creates, zero changes/deletes and retained orders/stock. No migrations, seeds, purchases or functional tests were run for this rebuild, as requested. The [00:37 results](docs/report/evidence/2026-11-10-restart/results.json) and existing source-build tag [`v0.1.0`](https://github.com/sxtay1914/IS458/tree/v0.1.0) record earlier successful verification, not a retest of this deployment. Teardown is paused after the owner's reversal; services remain running.

The November 7 inventory recorded three stopped Assignment3 EC2 instances, three 8 GB gp3 volumes and one unattached Elastic IP outside the demo. That is a dated inventory, not a fresh account-wide check.

## Tests that run without AWS

```bash
make db-local-up db-migrate          # MySQL 8 + Flyway in Docker
pip install -r functions/requirements-dev.txt
make test                            # terraform + pytest + store-api + storefront + e2e
```

## Deploy (short demo session)

These commands describe a fresh demo. The current rebuild preserved the database and skipped migration, seed and test commands.

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

Keep AWS and the local dashboard running for owner use; the current instruction is setup only, with no tests. Teardown is paused and there is no automatic shutdown or five-day runtime. When teardown is requested again, follow the staged checklist so Lambda execution permissions remain available until its network interfaces are released. `make destroy-demo` runs one full destroy and does not implement that staged sequence. The US$100 budget sends alerts and does not stop spending. The preflight billing snapshot showed about US$6.30 usage for November 1–9, offset by credits; it is delayed data, not a verified remaining-credit balance or final demo cost.
