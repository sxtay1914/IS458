# Whole-stack wiring test with a mocked AWS provider: every module composes,
# and the outputs the apps and manifests depend on are populated.
mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  owner                = "test"
  expires_on           = "2026-11-20"
  sender_email         = "orders@example.com"
  ses_recipient_emails = ["a@example.com"]
  packages_dir         = "/nonexistent"
}

run "full_stack_composes" {
  assert {
    condition     = startswith(output.storefront_url, "https://")
    error_message = "Storefront URL must be HTTPS"
  }
  assert {
    condition = toset(keys(output.app_config)) == toset([
      "AWS_REGION", "DB_HOST", "DB_NAME", "DB_SECRET_ARN", "CHECKOUT_QUEUE_URL",
      "CHECKOUT_STATUS_TOPIC_ARN", "COGNITO_ISSUER_URL", "COGNITO_CLIENT_ID",
      "COGNITO_DOMAIN", "STOREFRONT_URL",
    ])
    error_message = "app_config must expose every setting the apps read"
  }
  assert {
    condition     = toset(keys(output.target_group_arns)) == toset(["v1", "v2"])
    error_message = "Both pilot target groups exported"
  }
  assert {
    condition     = toset(keys(output.irsa_role_arns)) == toset(["store-api", "cluster-autoscaler", "aws-load-balancer-controller"])
    error_message = "IRSA roles exported for the service accounts"
  }
  assert {
    condition     = output.eks_cluster_name == "fashionstore-demo-eks"
    error_message = "Cluster name must match the subnet tags"
  }
  assert {
    condition     = length(output.function_names) == 4
    error_message = "Four Lambdas"
  }
}

run "rejects_bad_expiry_date" {
  command = plan
  variables {
    expires_on = "next friday"
  }
  expect_failures = [var.expires_on]
}
