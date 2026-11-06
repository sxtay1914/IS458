# FashionStore (IS458, Part B)

Implementation architecture for FashionStore on AWS Singapore (`ap-southeast-1`).
Terraform provisions AWS; Kubernetes, Kustomize and Helm configure EKS workloads.

* Current directory tree and repository boundaries: [Project Directory Structure](../FashionStore_Project_Directory_Structure.md)
* Plan, decisions, who-does-what, teardown: [docs/implementation-plan.md](docs/implementation-plan.md)
* What every folder and file is for: [docs/repository-guide.md](docs/repository-guide.md)
* Infrastructure: [infra/terraform/README.md](infra/terraform/README.md)
* Contracts between the halves: [contracts/README.md](contracts/README.md)
* Tests: [tests/README.md](tests/README.md)

Run commands below from `fashionstore/` (`cd fashionstore` from the IS458 Git root). Workflow definitions live at the Git root in `../.github/workflows/`, with working directories and paths configured for this application. GitHub can discover them once pushed; the AWS plan job also requires `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET`. Deploys use manual Makefile commands; no CD workflow exists.

## What is in the repo now

| Area | Status |
| --- | --- |
| `infra/terraform` (bootstrap + 10 service modules + bucket helper + demo env) | Built; 33 `terraform test` runs green (mocked AWS) |
| `database` (Flyway V001–V003, seeds, verify queries) | Built; migrates cleanly on MySQL 8.0 |
| `functions` (process-checkout, payment-api, notifier, report) | Built; 57 pytest tests green against real MySQL |
| `contracts` (OpenAPI, event schemas, examples) | Built; validated in Lambda and store-api tests |
| `platform` (Kustomize base/overlay, Flyway + seed Jobs, Helm values) | Built; overlay renders |
| `apps/store-api` (Spring Boot 3.5, Java 21) | Built; 24 tests green (Testcontainers MySQL); Docker image not built here |
| `apps/storefront` (React 19, Vite) | Built; 17 unit tests, typecheck and build green |
| `tests/e2e` (Playwright) | 4 browser journeys green against a mocked backend; live mode ready |
| `tests/security`, `correctness`, `failure` (pytest), `tests/load` (k6) | Written; need the deployed stack |

API and storefront tests were rerun locally for the checkout retry fix; other test results are recorded in the repository guide. Bootstrap has been applied to AWS (state bucket, GitHub OIDC roles and budget alerts). The demo stack has not been deployed.

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
# Export evidence, then destroy immediately after the demo:
make destroy-demo
```

Destroy demo resources immediately after the demo; do not leave them running for five days. Teardown is manual: follow the checklist in the plan; `make destroy-demo` covers steps 2–4. The US$100 budget sends alerts and does not automatically stop spending.
