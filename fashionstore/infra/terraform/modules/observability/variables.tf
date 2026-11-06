variable "name" {
  type = string
}

variable "ops_alerts_topic_arn" {
  type = string
}

variable "checkout_queue_name" {
  type = string
}

variable "checkout_dlq_name" {
  type = string
}

variable "notifier_failures_queue_name" {
  type = string
}

variable "function_names" {
  description = "Map from the functions module (process-checkout, notifier, report, ...)."
  type        = map(string)
}

variable "db_instance_id" {
  type = string
}

variable "alb_arn_suffix" {
  type = string
}

variable "target_group_arn_suffixes" {
  type = map(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}
