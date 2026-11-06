# FashionStore (IS458, Part B)

Implementation architecture for FashionStore on AWS Singapore (`ap-southeast-1`).
Terraform provisions AWS; Kubernetes, Kustomize and Helm configure EKS workloads.

* Plan and locked decisions: [docs/implementation-plan.md](docs/implementation-plan.md)
* Infrastructure: [infra/terraform/README.md](infra/terraform/README.md)

Part A (production target) is documentation only and is not provisioned.

## Quick start

```bash
make validate                 # fmt check + terraform validate, no AWS needed
make bootstrap                # once per account: state bucket, CI roles, budget
cp infra/terraform/environments/demo/{backend.hcl.example,backend.hcl}
cp infra/terraform/environments/demo/{terraform.tfvars.example,terraform.tfvars}
make init-demo deploy-demo
make destroy-demo             # at the end of the 5-day window
```
