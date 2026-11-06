variable "name" {
  type = string
}

variable "reports_expire_days" {
  description = "Reports move to IA at 30 days and Glacier at 90, then expire."
  type        = number
  default     = 365
}

variable "force_destroy" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
