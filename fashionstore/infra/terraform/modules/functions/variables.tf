variable "name" {
  type = string
}

variable "packages_dir" {
  description = "Directory holding <function>.zip files built by scripts/package-functions.sh."
  type        = string
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "subnet_ids" {
  description = "Subnets for in-VPC functions (AZ A private app subnet in Part B)."
  type        = list(string)
}

variable "security_group_id" {
  type = string
}

variable "db_host" {
  type = string
}

variable "db_port" {
  type    = number
  default = 3306
}

variable "db_name" {
  type = string
}

variable "db_secret_arn" {
  type = string
}

variable "checkout_queue_arn" {
  type = string
}

variable "checkout_status_topic_arn" {
  type = string
}

variable "notifier_failure_queue_arn" {
  type = string
}

variable "reports_bucket" {
  type = string
}

variable "reports_bucket_arn" {
  type = string
}

variable "sender_email" {
  description = "SES From address. Must be verified (sandbox)."
  type        = string
}

variable "ses_recipient_emails" {
  description = "Demo recipients to verify in the SES sandbox."
  type        = list(string)
  default     = []
}

variable "process_checkout_reserved_concurrency" {
  description = "Caps concurrent DB transactions to protect the db.t4g.micro."
  type        = number
  default     = 5

  validation {
    condition     = var.process_checkout_reserved_concurrency >= 2
    error_message = "SQS event source maximum concurrency is at least 2."
  }
}

variable "process_checkout_timeout_seconds" {
  description = "Keep the checkout queue visibility timeout at 6x this value or more."
  type        = number
  default     = 30
}

variable "payment_max_amount_cents" {
  type    = number
  default = 500000
}

variable "payment_decline_percent" {
  type    = number
  default = 0
}

variable "report_schedule_expression" {
  type    = string
  default = "cron(30 0 * * ? *)"
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "tags" {
  type    = map(string)
  default = {}
}
