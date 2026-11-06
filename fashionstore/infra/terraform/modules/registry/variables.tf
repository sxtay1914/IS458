variable "name" {
  type = string
}

variable "repositories" {
  description = "Repository short names; created as <name>/<repo>."
  type        = list(string)
  default     = ["store-api"]
}

variable "keep_images" {
  type    = number
  default = 5
}

variable "force_delete" {
  description = "Allow terraform destroy to delete repositories that still hold images (demo)."
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
