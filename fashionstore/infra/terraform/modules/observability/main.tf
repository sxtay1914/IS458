# Alarms -> SNS ops-alerts (email), plus one dashboard used as demo evidence.
# The cost budget lives in the bootstrap stack so it survives teardown.

data "aws_region" "current" {}

locals {
  region = data.aws_region.current.region

  alarms = {
    checkout-dlq-not-empty = {
      description = "A checkout failed 5 times and is in the DLQ. Inspect, fix, redrive."
      namespace   = "AWS/SQS"
      metric      = "ApproximateNumberOfMessagesVisible"
      dimensions  = { QueueName = var.checkout_dlq_name }
      statistic   = "Maximum"
      threshold   = 0
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    notifier-failures-not-empty = {
      description = "A shopper email failed after retries (notifier on-failure queue)."
      namespace   = "AWS/SQS"
      metric      = "ApproximateNumberOfMessagesVisible"
      dimensions  = { QueueName = var.notifier_failures_queue_name }
      statistic   = "Maximum"
      threshold   = 0
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    checkout-queue-backlog-age = {
      description = "Oldest checkout has waited more than 2 minutes."
      namespace   = "AWS/SQS"
      metric      = "ApproximateAgeOfOldestMessage"
      dimensions  = { QueueName = var.checkout_queue_name }
      statistic   = "Maximum"
      threshold   = 120
      periods     = 2
      comparison  = "GreaterThanThreshold"
    }
    process-checkout-errors = {
      description = "process-checkout invocations are failing."
      namespace   = "AWS/Lambda"
      metric      = "Errors"
      dimensions  = { FunctionName = var.function_names["process-checkout"] }
      statistic   = "Sum"
      threshold   = 0
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    process-checkout-throttles = {
      description = "process-checkout is throttled (reserved concurrency reached)."
      namespace   = "AWS/Lambda"
      metric      = "Throttles"
      dimensions  = { FunctionName = var.function_names["process-checkout"] }
      statistic   = "Sum"
      threshold   = 10
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    notifier-errors = {
      description = "notifier invocations are failing."
      namespace   = "AWS/Lambda"
      metric      = "Errors"
      dimensions  = { FunctionName = var.function_names["notifier"] }
      statistic   = "Sum"
      threshold   = 0
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    report-errors = {
      description = "The daily report failed."
      namespace   = "AWS/Lambda"
      metric      = "Errors"
      dimensions  = { FunctionName = var.function_names["report"] }
      statistic   = "Sum"
      threshold   = 0
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    rds-cpu-high = {
      description = "RDS CPU above 80% for 10 minutes."
      namespace   = "AWS/RDS"
      metric      = "CPUUtilization"
      dimensions  = { DBInstanceIdentifier = var.db_instance_id }
      statistic   = "Average"
      threshold   = 80
      periods     = 2
      comparison  = "GreaterThanThreshold"
    }
    rds-free-storage-low = {
      description = "RDS free storage below 2 GB."
      namespace   = "AWS/RDS"
      metric      = "FreeStorageSpace"
      dimensions  = { DBInstanceIdentifier = var.db_instance_id }
      statistic   = "Minimum"
      threshold   = 2147483648
      periods     = 1
      comparison  = "LessThanThreshold"
    }
    alb-target-5xx = {
      description = "store-api returned more than 10 5xx responses in 5 minutes."
      namespace   = "AWS/ApplicationELB"
      metric      = "HTTPCode_Target_5XX_Count"
      dimensions  = { LoadBalancer = var.alb_arn_suffix }
      statistic   = "Sum"
      threshold   = 10
      periods     = 1
      comparison  = "GreaterThanThreshold"
    }
    api-v1-unhealthy = {
      description = "A store-api v1 target is unhealthy."
      namespace   = "AWS/ApplicationELB"
      metric      = "UnHealthyHostCount"
      dimensions  = { LoadBalancer = var.alb_arn_suffix, TargetGroup = var.target_group_arn_suffixes["v1"] }
      statistic   = "Maximum"
      threshold   = 0
      periods     = 2
      comparison  = "GreaterThanThreshold"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "this" {
  for_each = local.alarms

  alarm_name          = "${var.name}-${each.key}"
  alarm_description   = each.value.description
  namespace           = each.value.namespace
  metric_name         = each.value.metric
  dimensions          = each.value.dimensions
  statistic           = each.value.statistic
  period              = 300
  evaluation_periods  = each.value.periods
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.ops_alerts_topic_arn]
  ok_actions          = [var.ops_alerts_topic_arn]
  tags                = var.tags
}

resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = "${var.name}-overview"

  dashboard_body = jsonencode({
    start          = "-PT15M"
    periodOverride = "inherit"
    widgets = [
      {
        type = "alarm", x = 0, y = 0, width = 24, height = 4
        properties = {
          title  = "System Safety & Ops Alarms"
          alarms = [for k, a in aws_cloudwatch_metric_alarm.this : a.arn]
        }
      },
      {
        type = "metric", x = 0, y = 4, width = 12, height = 6
        properties = {
          title  = "Checkout queue"
          region = local.region
          stat   = "Maximum"
          period = 60
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.checkout_queue_name, { label = "Visible Messages" }],
            ["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", var.checkout_queue_name, { yAxis = "right", label = "Oldest Age (s)" }],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.checkout_dlq_name, { label = "DLQ depth (Poison/Failed)" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 4, width = 12, height = 6
        properties = {
          title  = "process-checkout"
          region = local.region
          stat   = "Sum"
          period = 60
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.function_names["process-checkout"], { label = "Invocations" }],
            ["AWS/Lambda", "Errors", "FunctionName", var.function_names["process-checkout"], { label = "Errors" }],
            ["AWS/Lambda", "Throttles", "FunctionName", var.function_names["process-checkout"], { label = "Throttles" }],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", var.function_names["process-checkout"], { stat = "Maximum", yAxis = "right", label = "Max Concurrency" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 10, width = 12, height = 6
        properties = {
          title  = "Payment API Failures & Worker Retries"
          region = local.region
          stat   = "Sum"
          period = 60
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.function_names["payment-api"], { label = "payment-api Invocations" }],
            ["AWS/Lambda", "Throttles", "FunctionName", var.function_names["payment-api"], { label = "payment-api Throttles (Failure Injection)" }],
            ["AWS/Lambda", "Errors", "FunctionName", var.function_names["payment-api"], { label = "payment-api Errors" }],
            ["AWS/Lambda", "Errors", "FunctionName", var.function_names["process-checkout"], { yAxis = "right", label = "process-checkout Errors" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 10, width = 12, height = 6
        properties = {
          title  = "ALB Target Group Health & 5XX Errors"
          region = local.region
          stat   = "Average"
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", var.target_group_arn_suffixes["v1"], "LoadBalancer", var.alb_arn_suffix, { stat = "Minimum", label = "v1 Healthy Hosts" }],
            ["AWS/ApplicationELB", "UnHealthyHostCount", "TargetGroup", var.target_group_arn_suffixes["v1"], "LoadBalancer", var.alb_arn_suffix, { stat = "Maximum", label = "v1 Unhealthy Hosts" }],
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", var.target_group_arn_suffixes["v2"], "LoadBalancer", var.alb_arn_suffix, { stat = "Minimum", label = "v2 Healthy Hosts" }],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", var.alb_arn_suffix, { stat = "Sum", yAxis = "right", label = "Target 5XX Errors (Zero Downtime)" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 16, width = 12, height = 6
        properties = {
          title  = "Pilot split: requests per target group"
          region = local.region
          stat   = "Sum"
          period = 60
          metrics = [
            ["AWS/ApplicationELB", "RequestCountPerTarget", "TargetGroup", var.target_group_arn_suffixes["v1"], "LoadBalancer", var.alb_arn_suffix, { label = "v1" }],
            ["AWS/ApplicationELB", "RequestCountPerTarget", "TargetGroup", var.target_group_arn_suffixes["v2"], "LoadBalancer", var.alb_arn_suffix, { label = "v2" }],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix, { stat = "p95", yAxis = "right", label = "p95 latency (s)" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 16, width = 12, height = 6
        properties = {
          title  = "RDS"
          region = local.region
          stat   = "Average"
          period = 60
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.db_instance_id],
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", var.db_instance_id, { yAxis = "right" }],
          ]
        }
      },
    ]
  })
}
