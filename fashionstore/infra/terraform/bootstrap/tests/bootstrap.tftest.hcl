mock_provider "aws" {
  source = "../tests/mocks"
}

variables {
  github_repository   = "my-team/fashionstore"
  budget_alert_emails = ["lead@example.com"]
}

run "state_bucket_and_budget" {
  assert {
    condition     = aws_s3_bucket.state.bucket == "fashionstore-tfstate-123456789012"
    error_message = "State bucket name includes the account id"
  }
  assert {
    condition     = aws_s3_bucket_versioning.state.versioning_configuration[0].status == "Enabled"
    error_message = "State bucket must be versioned"
  }
  assert {
    condition     = aws_budgets_budget.build.limit_amount == "100"
    error_message = "Budget is $100"
  }
  assert {
    condition     = toset([for n in aws_budgets_budget.build.notification : "${n.notification_type}:${n.threshold}"]) == toset(["ACTUAL:50", "ACTUAL:80", "FORECASTED:100"])
    error_message = "Alerts at 50%, 80% actual and 100% forecast"
  }
}

run "github_oidc_roles" {
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 1
    error_message = "Creates the GitHub OIDC provider by default"
  }
  assert {
    condition     = strcontains(output.demo_backend_hcl, "use_lockfile = true")
    error_message = "Backend uses S3 native locking"
  }
}

run "reuse_existing_oidc_provider" {
  variables {
    create_github_oidc_provider = false
  }
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 0
    error_message = "Must not create a second provider"
  }
}

run "rejects_bad_repo_name" {
  command = plan
  variables {
    github_repository = "not a repo"
  }
  expect_failures = [var.github_repository]
}
