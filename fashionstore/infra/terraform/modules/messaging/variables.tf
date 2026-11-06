variable "name" {
  type = string
}

variable "checkout_visibility_timeout_seconds" {
  description = "At least 6x the process-checkout timeout (AWS guidance for SQS event sources)."
  type        = number
  default     = 180
}

variable "max_receive_count" {
  description = "Receives before a checkout message moves to the DLQ."
  type        = number
  default     = 5
}

variable "ops_alert_emails" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
