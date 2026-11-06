# Terraform

Bootstrap was applied on 2026-11-06. The demo stack remains undeployed. Use the signed-in `fashionstore` AWS CLI profile (`AWS_PROFILE=fashionstore`) for local AWS/Terraform commands.

Two kinds of stack, with separate state:

| Stack | Lifetime | Holds |
| --- | --- | --- |
| `bootstrap/` | Whole project (local state) | S3 state bucket (versioned, S3-native locking), GitHub OIDC provider, `fashionstore-github-plan` and `fashionstore-github-apply` roles, $100 budget with 50% / 80% / forecast-100% alerts |
| `environments/demo/` | Demo session only; destroy immediately afterwards | Everything else, composed from `modules/` |

Requires Terraform >= 1.10 (S3 `use_lockfile`) and AWS provider 6.x. Tested with Terraform 1.13.4 and AWS provider 6.72.0.

## Modules

| Module | What it builds | Key decisions |
| --- | --- | --- |
| `network` | VPC 10.10.0.0/16, L1/L2/L3 × 2 AZs, IGW, one NAT (AZ A), S3 gateway endpoint, SGs | DB SG has no egress; ALB SG only from the CloudFront origin-facing prefix list |
| `registry` | ECR `fashionstore-demo/store-api` | Immutable tags, scan on push, keep last 5 images |
| `database` | RDS MySQL 8.0 db.t4g.micro, single-AZ in AZ A, isolated subnets | RDS-managed password in Secrets Manager, 1-day backups, no final snapshot |
| `messaging` | SQS `checkout-requests` + DLQ (maxReceiveCount 5), `notifier-failures` SQS, SNS `checkout-status`, SNS `ops-alerts` | Visibility timeout 180 s = 6 × Lambda timeout |
| `analytics` | Reports bucket (IA 30 d → Glacier 90 d), Athena results bucket (expire 7 d), Athena workgroup, Glue tables with partition projection, 2 named queries | 100 MB scan guardrail per query |
| `functions` | 4 Python 3.12 arm64 Lambdas, one IAM role each, 7-day log groups, SQS mapping, SNS subscription, EventBridge Scheduler, SES identities | process-checkout reserved concurrency 5 and SQS max concurrency 5; payment-api outside the VPC |
| `eks` | EKS 1.33 (access entries), t3.medium node group 1/2/3 in AZ A, IRSA for store-api, Cluster Autoscaler, LB controller | `ignore_changes` on `desired_size`; LB controller only gets TargetGroupBinding permissions |
| `delivery` | Internal ALB, v1/v2 IP target groups weighted 90/10 on `/api/*`, private S3 + OAC, CloudFront VPC origin, SPA rewrite function | No distribution-wide error pages (they would hide API 404s) |
| `identity` | Cognito user pool, hosted domain, public SPA client (code + PKCE), resource server scopes | Classic hosted UI (`managed_login_version = 1`) so tests can sign in by script; no `USER_PASSWORD_AUTH` (its tokens lack the API scopes) |
| `observability` | 11 alarms to `ops-alerts`, one dashboard (queue, Lambda, pilot split, RDS) | Budget lives in bootstrap so it outlives the demo stack |
| `private-bucket` | Shared helper: private, encrypted, TLS-only bucket | |

## Network

```
VPC 10.10.0.0/16                AZ A (workloads)        AZ B (subnets only)
L1 public      IGW, NAT         10.10.1.0/24  NAT GW    10.10.2.0/24
L2 private app nodes, ALB, λ    10.10.3.0/24            10.10.4.0/24
L3 isolated    RDS              10.10.5.0/24            10.10.6.0/24
```

The **internal ALB sits in L2**, not L1 as on the slide. CloudFront reaches it through a VPC origin, so nothing in the VPC is internet-facing except the NAT.

**Open check:** CloudFront VPC origins may connect from the service-managed `CloudFront-VPCOrigins-Service-SG` instead of prefix-list addresses. If `make verify-private` reports 502 or 504 on `/api/*`, add that SG's id to `alb_extra_source_security_group_ids` and apply again.

## Tests

`make tf-test` runs `terraform test` in every module, in bootstrap and in the demo environment against a **mocked** AWS provider (`tests/mocks/aws.tfmock.hcl`), so no credentials or AWS costs are needed. The tests check the decisions above (CIDRs, single NAT, SG sources, t3.medium 1/2/3, reserved concurrency 5, 90/10 weights, VPC origin, PKCE, budget thresholds, …) and that the whole stack composes. They can't prove AWS will accept every value. Only a real `plan` and `apply` can do that.

## First run

Run from `fashionstore/infra/terraform`. Set bootstrap `github_repository = "sxtay1914/IS458"` for the existing repository. Workflow definitions are at the Git root in `.github/workflows/` with monorepo paths; push them and verify their first GitHub run. The plan job requires repository variables `AWS_PLAN_ROLE_ARN` and `TF_STATE_BUCKET`. The apply role exists, but no CD workflow uses it yet.

```bash
cd bootstrap
cp terraform.tfvars.example terraform.tfvars    # repo name, alert emails
terraform init && terraform apply
terraform output -raw demo_backend_hcl > ../environments/demo/backend.hcl

cd ../environments/demo
cp terraform.tfvars.example terraform.tfvars    # owner, expires_on, SES addresses
cd ../../../.. && make init-demo deploy-demo     # packages the Lambdas first
```

The demo apply provisions EKS and CloudFront; allow setup time, then destroy immediately after the demo. Budget alerts do not automatically stop charges. Keep `bootstrap/terraform.tfstate` somewhere safe outside git.
