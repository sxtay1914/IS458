# Checkout queue + DLQ, the checkout-status and ops-alerts topics, and the
# notifier failure queue (on-failure destination for async invokes).

resource "aws_sqs_queue" "checkout_dlq" {
  name                      = "${var.name}-checkout-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true
  tags                      = var.tags
}

resource "aws_sqs_queue" "checkout_requests" {
  name                       = "${var.name}-checkout-requests"
  visibility_timeout_seconds = var.checkout_visibility_timeout_seconds
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.checkout_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}

resource "aws_sqs_queue_redrive_allow_policy" "checkout_dlq" {
  queue_url = aws_sqs_queue.checkout_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.checkout_requests.arn]
  })
}

resource "aws_sqs_queue" "notifier_failures" {
  name                      = "${var.name}-notifier-failures"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = var.tags
}

resource "aws_sns_topic" "checkout_status" {
  name              = "${var.name}-checkout-status"
  kms_master_key_id = "alias/aws/sns"
  tags              = var.tags
}

resource "aws_sns_topic" "ops_alerts" {
  name = "${var.name}-ops-alerts"
  # Unencrypted on purpose: CloudWatch alarms cannot publish to a topic that
  # uses the AWS-managed SNS key.
  tags = var.tags
}

resource "aws_sns_topic_subscription" "ops_email" {
  for_each  = toset(var.ops_alert_emails)
  topic_arn = aws_sns_topic.ops_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}
