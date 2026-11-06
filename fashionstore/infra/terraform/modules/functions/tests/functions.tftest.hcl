mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name                       = "fs-test"
  packages_dir               = "/nonexistent"
  subnet_ids                 = ["subnet-a"]
  security_group_id          = "sg-lambda"
  db_host                    = "db.internal"
  db_name                    = "fashionstore"
  db_secret_arn              = "arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:rds!db-1"
  checkout_queue_arn         = "arn:aws:sqs:ap-southeast-1:123456789012:fs-test-checkout-requests"
  checkout_status_topic_arn  = "arn:aws:sns:ap-southeast-1:123456789012:fs-test-checkout-status"
  notifier_failure_queue_arn = "arn:aws:sqs:ap-southeast-1:123456789012:fs-test-notifier-failures"
  reports_bucket             = "fs-test-reports"
  reports_bucket_arn         = "arn:aws:s3:::fs-test-reports"
  sender_email               = "orders@example.com"
  ses_recipient_emails       = ["a@example.com", "orders@example.com"]
}

run "checkout_is_capped_to_protect_rds" {
  assert {
    condition     = aws_lambda_function.this["process-checkout"].reserved_concurrent_executions == 5
    error_message = "process-checkout reserved concurrency must be 5"
  }
  assert {
    condition     = aws_lambda_event_source_mapping.checkout.scaling_config[0].maximum_concurrency == 5
    error_message = "SQS poller concurrency must match reserved concurrency"
  }
  assert {
    condition     = contains(aws_lambda_event_source_mapping.checkout.function_response_types, "ReportBatchItemFailures")
    error_message = "Partial batch responses must be enabled"
  }
  assert {
    condition     = aws_lambda_event_source_mapping.checkout.batch_size <= 10
    error_message = "Keep batches small"
  }
}

run "vpc_placement" {
  assert {
    condition     = length(aws_lambda_function.this["payment-api"].vpc_config) == 0
    error_message = "payment-api runs outside the VPC"
  }
  assert {
    condition = alltrue([for f in ["process-checkout", "notifier", "report"] :
    aws_lambda_function.this[f].vpc_config[0].subnet_ids == toset(["subnet-a"])])
    error_message = "DB-facing functions run in the VPC"
  }
}

run "wiring_and_env" {
  assert {
    condition     = aws_lambda_function.this["process-checkout"].environment[0].variables["PAYMENT_FUNCTION_NAME"] == "fs-test-payment-api"
    error_message = "process-checkout must call payment-api by name"
  }
  assert {
    condition     = aws_lambda_function.this["notifier"].environment[0].variables["LEASE_SECONDS"] == "120" && aws_lambda_function.this["notifier"].timeout < 120
    error_message = "Notifier lease must outlive the function timeout"
  }
  assert {
    condition     = aws_sns_topic_subscription.notifier.protocol == "lambda"
    error_message = "notifier subscribes to checkout-status"
  }
  assert {
    condition     = aws_lambda_function_event_invoke_config.notifier.destination_config[0].on_failure[0].destination == var.notifier_failure_queue_arn
    error_message = "Failed notifications go to the failure queue"
  }
  assert {
    condition     = jsondecode(aws_scheduler_schedule.report.target[0].input).date == "yesterday"
    error_message = "Daily report covers the previous day"
  }
  assert {
    condition     = length(aws_sesv2_email_identity.this) == 2
    error_message = "Sender + recipients verified once each"
  }
  assert {
    condition     = alltrue([for g in aws_cloudwatch_log_group.this : g.retention_in_days == 7])
    error_message = "7-day log retention"
  }
}

run "rejects_concurrency_below_two" {
  command = plan
  variables {
    process_checkout_reserved_concurrency = 1
  }
  expect_failures = [var.process_checkout_reserved_concurrency]
}
