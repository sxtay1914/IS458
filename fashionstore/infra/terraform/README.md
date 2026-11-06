# Terraform

Two kinds of stack, with separate state:

| Stack | Lifetime | Holds |
| --- | --- | --- |
| `bootstrap/` | Whole project (local state) | S3 state bucket (versioned, S3-native locking), GitHub OIDC provider, `fashionstore-github-plan` and `fashionstore-github-apply` roles, $100 budget with 50% / 80% / forecast-100% alerts |
| `environments/demo/` | 5-day window, then destroyed | Everything else, composed from `modules/` |

Requires Terraform >= 1.10 (S3 `use_lockfile`) and AWS provider 6.x.

## Network (built)

```
VPC 10.10.0.0/16                AZ A (workloads)        AZ B (subnets only)
L1 public      IGW, NAT         10.10.1.0/24  NAT GW    10.10.2.0/24
L2 private app nodes, ALB, λ    10.10.3.0/24            10.10.4.0/24
L3 isolated    RDS              10.10.5.0/24            10.10.6.0/24
```

* **Internal ALB in L2**, not L1. CloudFront reaches it through a VPC origin, so
  nothing in the VPC is internet-facing except the NAT. This changes the slide,
  where the ALB sits in L1.
* One NAT in AZ A; both private subnets route through it. Isolated subnets have
  only the local route.
* S3 gateway endpoint on the private and isolated route tables.
* Security groups: `alb` (from the CloudFront origin-facing prefix list),
  `app` (from `alb` on 8080), `lambda`, `database` (3306 from `app` and
  `lambda` only, no egress). The default SG is emptied.
* Private subnets carry `kubernetes.io/role/internal-elb` and the cluster tag.

When the `eks` module is added, attach `security_group_ids.app` to the node
group's launch template. The EKS cluster security group still handles
node-to-node and control-plane traffic.

**Open check:** CloudFront VPC origins may connect from the service-managed
`CloudFront-VPCOrigins-Service-SG` instead of prefix-list addresses. If
`/api/*` returns 502 or 504 through CloudFront, add that SG's id to
`alb_extra_source_security_group_ids`.

## First run

```bash
cd bootstrap
cp terraform.tfvars.example terraform.tfvars    # repo name, alert emails
terraform init && terraform apply
terraform output -raw demo_backend_hcl > ../environments/demo/backend.hcl

cd ../environments/demo
cp terraform.tfvars.example terraform.tfvars    # owner, expires_on
terraform init -backend-config=backend.hcl
terraform plan
```

Keep `bootstrap/terraform.tfstate` somewhere safe outside git (for example a
team drive). Losing it only means importing three or four resources, but avoid it.
