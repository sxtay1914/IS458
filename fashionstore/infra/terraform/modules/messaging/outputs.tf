output "checkout_queue_url" {
  value = aws_sqs_queue.checkout_requests.id
}

output "checkout_queue_arn" {
  value = aws_sqs_queue.checkout_requests.arn
}

output "checkout_queue_name" {
  value = aws_sqs_queue.checkout_requests.name
}

output "checkout_dlq_arn" {
  value = aws_sqs_queue.checkout_dlq.arn
}

output "checkout_dlq_name" {
  value = aws_sqs_queue.checkout_dlq.name
}

output "checkout_dlq_url" {
  value = aws_sqs_queue.checkout_dlq.id
}

output "notifier_failures_queue_arn" {
  value = aws_sqs_queue.notifier_failures.arn
}

output "notifier_failures_queue_name" {
  value = aws_sqs_queue.notifier_failures.name
}

output "checkout_status_topic_arn" {
  value = aws_sns_topic.checkout_status.arn
}

output "ops_alerts_topic_arn" {
  value = aws_sns_topic.ops_alerts.arn
}
