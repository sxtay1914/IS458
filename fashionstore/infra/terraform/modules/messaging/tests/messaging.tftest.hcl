mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name             = "fs-test"
  ops_alert_emails = ["ops@example.com"]
}

run "dlq_and_timeouts" {
  assert {
    condition     = jsondecode(aws_sqs_queue.checkout_requests.redrive_policy).maxReceiveCount == 5
    error_message = "maxReceiveCount must be 5"
  }
  assert {
    condition     = aws_sqs_queue.checkout_requests.visibility_timeout_seconds >= 6 * 30
    error_message = "Visibility timeout must be at least 6x the 30s Lambda timeout"
  }
  assert {
    condition     = aws_sqs_queue.checkout_dlq.message_retention_seconds == 1209600
    error_message = "DLQ keeps messages 14 days"
  }
  assert {
    condition     = aws_sqs_queue.checkout_requests.sqs_managed_sse_enabled
    error_message = "Queues are encrypted"
  }
  assert {
    condition     = length(aws_sns_topic_subscription.ops_email) == 1
    error_message = "Ops alert email subscribed"
  }
}
