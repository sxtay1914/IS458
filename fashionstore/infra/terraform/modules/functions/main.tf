# Lambdas, their roles, log groups and event bindings:
#   SQS checkout-requests -> process-checkout (reserved concurrency 5) -> payment-api
#   SNS checkout-status   -> notifier -> SES   (on failure -> notifier-failures SQS)
#   EventBridge Scheduler -> report -> S3 reports

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region
  partition  = data.aws_partition.current.partition

  db_env = {
    DB_HOST       = var.db_host
    DB_PORT       = tostring(var.db_port)
    DB_NAME       = var.db_name
    DB_SECRET_ARN = var.db_secret_arn
  }

  functions = {
    "process-checkout" = {
      description = "Consumes checkout-requests; one RDS transaction per checkout"
      timeout     = var.process_checkout_timeout_seconds
      memory      = 256
      in_vpc      = true
      reserved    = var.process_checkout_reserved_concurrency
      env = merge(local.db_env, {
        PAYMENT_FUNCTION_NAME = "${var.name}-payment-api"
        STATUS_TOPIC_ARN      = var.checkout_status_topic_arn
      })
    }
    "payment-api" = {
      description = "Simulated, deterministic payment gateway"
      timeout     = 10
      memory      = 128
      in_vpc      = false
      reserved    = -1
      env = {
        MAX_AMOUNT_CENTS = tostring(var.payment_max_amount_cents)
        DECLINE_PERCENT  = tostring(var.payment_decline_percent)
      }
    }
    "notifier" = {
      description = "checkout-status -> notification_log -> SES"
      timeout     = 30
      memory      = 256
      in_vpc      = true
      reserved    = -1
      env = merge(local.db_env, {
        SENDER_EMAIL  = var.sender_email
        LEASE_SECONDS = "120"
      })
    }
    "report" = {
      description = "Daily sales and stock CSVs for Athena"
      timeout     = 120
      memory      = 256
      in_vpc      = true
      reserved    = -1
      env = merge(local.db_env, {
        REPORTS_BUCKET = var.reports_bucket
      })
    }
  }

  function_names = { for k, _ in local.functions : k => "${var.name}-${k}" }
}

# ---------------------------------------------------------------------------
# Logs (7-day retention, destroyed with the stack)
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "this" {
  for_each          = local.functions
  name              = "/aws/lambda/${local.function_names[each.key]}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# ---------------------------------------------------------------------------
# IAM: one role per function, least privilege
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  for_each           = local.functions
  name               = "${local.function_names[each.key]}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  for_each   = local.functions
  role       = aws_iam_role.this[each.key].name
  policy_arn = each.value.in_vpc ? "arn:${local.partition}:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole" : "arn:${local.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "process_checkout" {
  statement {
    sid       = "ConsumeCheckoutQueue"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
    resources = [var.checkout_queue_arn]
  }
  statement {
    sid       = "InvokePayment"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.this["payment-api"].arn]
  }
  statement {
    sid       = "PublishOutcome"
    actions   = ["sns:Publish"]
    resources = [var.checkout_status_topic_arn]
  }
  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arn]
  }
}

data "aws_iam_policy_document" "notifier" {
  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arn]
  }
  statement {
    sid     = "SendEmail"
    actions = ["ses:SendEmail"]
    # In the SES sandbox the recipient identities are checked too, so allow all
    # identities in this account and region, but only From the sender address.
    resources = ["arn:${local.partition}:ses:${local.region}:${local.account_id}:identity/*"]
    condition {
      test     = "StringEquals"
      variable = "ses:FromAddress"
      values   = [var.sender_email]
    }
  }
  statement {
    sid       = "OnFailureDestination"
    actions   = ["sqs:SendMessage"]
    resources = [var.notifier_failure_queue_arn]
  }
}

data "aws_iam_policy_document" "report" {
  statement {
    sid       = "ReadDbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.db_secret_arn]
  }
  statement {
    sid       = "WriteReports"
    actions   = ["s3:PutObject"]
    resources = ["${var.reports_bucket_arn}/reports/*"]
  }
}

locals {
  inline_policies = {
    "process-checkout" = data.aws_iam_policy_document.process_checkout.json
    "notifier"         = data.aws_iam_policy_document.notifier.json
    "report"           = data.aws_iam_policy_document.report.json
  }
}

resource "aws_iam_role_policy" "this" {
  for_each = local.inline_policies
  name     = "${local.function_names[each.key]}-policy"
  role     = aws_iam_role.this[each.key].id
  policy   = each.value
}

# ---------------------------------------------------------------------------
# Functions. Packages are built by scripts/package-functions.sh into
# var.packages_dir/<function>.zip before plan/apply.
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "this" {
  for_each = local.functions

  function_name    = local.function_names[each.key]
  description      = each.value.description
  role             = aws_iam_role.this[each.key].arn
  runtime          = var.runtime
  architectures    = ["arm64"]
  handler          = "handler.lambda_handler"
  filename         = "${var.packages_dir}/${each.key}.zip"
  source_code_hash = try(filebase64sha256("${var.packages_dir}/${each.key}.zip"), null)
  timeout          = each.value.timeout
  memory_size      = each.value.memory

  reserved_concurrent_executions = each.value.reserved

  environment {
    variables = merge(each.value.env, { LOG_LEVEL = "INFO" })
  }

  dynamic "vpc_config" {
    for_each = each.value.in_vpc ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = [var.security_group_id]
    }
  }

  tags = merge(var.tags, { Name = local.function_names[each.key] })

  depends_on = [
    aws_cloudwatch_log_group.this,
    aws_iam_role_policy_attachment.execution,
  ]
}

# ---------------------------------------------------------------------------
# Event bindings
# ---------------------------------------------------------------------------

resource "aws_lambda_event_source_mapping" "checkout" {
  event_source_arn                   = var.checkout_queue_arn
  function_name                      = aws_lambda_function.this["process-checkout"].arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 1
  function_response_types            = ["ReportBatchItemFailures"]

  # Matches reserved concurrency so the poller never over-invokes and gets throttled.
  scaling_config {
    maximum_concurrency = max(2, var.process_checkout_reserved_concurrency)
  }

  depends_on = [aws_iam_role_policy.this]
}

resource "aws_sns_topic_subscription" "notifier" {
  topic_arn = var.checkout_status_topic_arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.this["notifier"].arn
}

resource "aws_lambda_permission" "notifier_from_sns" {
  statement_id  = "AllowCheckoutStatusTopic"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this["notifier"].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.checkout_status_topic_arn
}

resource "aws_lambda_function_event_invoke_config" "notifier" {
  function_name                = aws_lambda_function.this["notifier"].function_name
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600

  destination_config {
    on_failure {
      destination = var.notifier_failure_queue_arn
    }
  }

  depends_on = [aws_iam_role_policy.this]
}

# SES sandbox: the sender and every demo recipient must be verified identities.
resource "aws_sesv2_email_identity" "this" {
  for_each       = toset(distinct(concat([var.sender_email], var.ses_recipient_emails)))
  email_identity = each.value
  tags           = var.tags
}

data "aws_iam_policy_document" "assume_scheduler" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.name}-report-scheduler"
  assume_role_policy = data.aws_iam_policy_document.assume_scheduler.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${var.name}-report-scheduler"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.this["report"].arn
    }]
  })
}

resource "aws_scheduler_schedule" "report" {
  name                         = "${var.name}-report-daily"
  description                  = "Daily sales and stock report for the previous UTC day"
  schedule_expression          = var.report_schedule_expression
  schedule_expression_timezone = "UTC"
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.this["report"].arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ date = "yesterday" })

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}
