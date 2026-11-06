variable "project" {
  type    = string
  default = "fashionstore"
}

variable "environment" {
  type    = string
  default = "demo"
}

variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "azs" {
  description = "AZ A runs all workloads; AZ B holds subnets only."
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}

variable "vpc_cidr" {
  type    = string
  default = "10.10.0.0/16"
}

variable "owner" {
  description = "Team or person accountable for this stack (tag)."
  type        = string
}

variable "expires_on" {
  description = "Date the stack must be destroyed by, YYYY-MM-DD (tag; the window is 5 days)."
  type        = string

  validation {
    condition     = can(regex("^\\d{4}-\\d{2}-\\d{2}$", var.expires_on))
    error_message = "Use YYYY-MM-DD."
  }
}

variable "alb_extra_source_security_group_ids" {
  description = "Set to [CloudFront-VPCOrigins-Service-SG id] only if CloudFront cannot reach the ALB via the prefix list."
  type        = list(string)
  default     = []
}

variable "packages_dir" {
  description = "Where scripts/package-functions.sh wrote the Lambda zips. Defaults to <repo>/build/functions."
  type        = string
  default     = null
}

variable "sender_email" {
  description = "SES From address (verified identity; sandbox)."
  type        = string
}

variable "ses_recipient_emails" {
  description = "Every demo shopper address. In the SES sandbox each must click its verification email."
  type        = list(string)
  default     = []
}

variable "ops_alert_emails" {
  description = "Receive CloudWatch alarm emails (confirm the SNS subscription)."
  type        = list(string)
  default     = []
}

variable "eks_public_access_cidrs" {
  description = "CIDRs allowed to reach the EKS API endpoint. Narrow to your IPs."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "eks_admin_principal_arns" {
  description = "Teammates' IAM role/user ARNs and the CI apply role, granted cluster admin."
  type        = list(string)
  default     = []
}

variable "v1_weight" {
  type    = number
  default = 90
}

variable "v2_weight" {
  type    = number
  default = 10
}

variable "payment_decline_percent" {
  description = "Simulated card decline rate for demos (0-100)."
  type        = number
  default     = 0
}
