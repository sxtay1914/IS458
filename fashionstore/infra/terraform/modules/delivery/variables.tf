variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "alb_subnet_ids" {
  description = "Private app subnets in two AZs (an ALB needs two)."
  type        = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "health_check_path" {
  type    = string
  default = "/actuator/health/readiness"
}

variable "v1_weight" {
  description = "Share of /api/* traffic sent to v1 (stable)."
  type        = number
  default     = 90
}

variable "v2_weight" {
  description = "Share of /api/* traffic sent to v2 (pilot)."
  type        = number
  default     = 10

  validation {
    condition     = var.v2_weight >= 0 && var.v2_weight <= 999
    error_message = "ALB weights are 0..999."
  }
}

variable "price_class" {
  description = "PriceClass_200 includes Asia edge locations and costs less than PriceClass_All."
  type        = string
  default     = "PriceClass_200"
}

variable "tags" {
  type    = map(string)
  default = {}
}
