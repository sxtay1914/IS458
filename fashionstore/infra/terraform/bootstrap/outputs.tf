output "state_bucket" {
  description = "S3 bucket that holds remote state for every other stack."
  value       = aws_s3_bucket.state.bucket
}

output "github_plan_role_arn" {
  description = "Role for terraform plan in pull-request workflows."
  value       = aws_iam_role.github_plan.arn
}

output "github_apply_role_arn" {
  description = "Role for terraform apply on the apply branch or the demo environment."
  value       = aws_iam_role.github_apply.arn
}

output "demo_backend_hcl" {
  description = "Paste into infra/terraform/environments/demo/backend.hcl."
  value       = <<-EOT
    bucket       = "${aws_s3_bucket.state.bucket}"
    key          = "demo/terraform.tfstate"
    region       = "${var.region}"
    encrypt      = true
    use_lockfile = true
  EOT
}
