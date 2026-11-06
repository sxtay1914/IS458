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
