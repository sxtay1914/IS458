mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name                         = "fs-test"
  ops_alerts_topic_arn         = "arn:aws:sns:ap-southeast-1:123456789012:ops"
  checkout_queue_name          = "fs-test-checkout-requests"
  checkout_dlq_name            = "fs-test-checkout-dlq"
  notifier_failures_queue_name = "fs-test-notifier-failures"
  function_names               = { "process-checkout" = "fs-test-process-checkout", notifier = "fs-test-notifier", report = "fs-test-report", "payment-api" = "fs-test-payment-api" }
  db_instance_id               = "fs-test-mysql"
  alb_arn_suffix               = "app/fs-test-api/123"
  target_group_arn_suffixes    = { v1 = "targetgroup/v1/1", v2 = "targetgroup/v2/2" }
}

run "dlq_alarm_fires_on_first_message" {
  assert {
    condition     = aws_cloudwatch_metric_alarm.this["checkout-dlq-not-empty"].threshold == 0 && aws_cloudwatch_metric_alarm.this["checkout-dlq-not-empty"].comparison_operator == "GreaterThanThreshold"
    error_message = "DLQ alarm must fire when depth > 0"
  }
  assert {
    condition     = aws_cloudwatch_metric_alarm.this["rds-free-storage-low"].comparison_operator == "LessThanThreshold"
    error_message = "Storage alarm compares downwards"
  }
  assert {
    condition     = alltrue([for a in aws_cloudwatch_metric_alarm.this : contains(a.alarm_actions, var.ops_alerts_topic_arn)])
    error_message = "Every alarm notifies ops-alerts"
  }
}
