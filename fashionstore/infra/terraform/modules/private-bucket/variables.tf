variable "bucket" {
  type = string
}

variable "force_destroy" {
  description = "Let terraform destroy delete a non-empty bucket (demo)."
  type        = bool
  default     = true
}

variable "extra_policy_statements" {
  description = "Additional bucket policy statements, as objects."
  type        = any
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
