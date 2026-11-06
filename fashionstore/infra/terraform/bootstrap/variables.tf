variable "project" {
  description = "Project name, used as a prefix for every resource."
  type        = string
  default     = "fashionstore"
}

variable "region" {
  description = "AWS region for the state bucket and IAM-adjacent resources."
  type        = string
  default     = "ap-southeast-1"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the CI roles, as owner/name."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Use the form owner/name, for example my-team/fashionstore."
  }
}

variable "github_apply_branch" {
  description = "Branch whose workflows may assume the apply role."
  type        = string
  default     = "main"
}

variable "create_github_oidc_provider" {
  description = "Set false if the account already has the token.actions.githubusercontent.com provider."
  type        = bool
  default     = true
}

variable "budget_limit_usd" {
  description = "Monthly cost budget in USD."
  type        = number
  default     = 100
}

variable "budget_alert_emails" {
  description = "Addresses that receive the 50% / 80% / 100%-forecast budget alerts."
  type        = list(string)

  validation {
    condition     = length(var.budget_alert_emails) > 0
    error_message = "Give at least one address for budget alerts."
  }
}
