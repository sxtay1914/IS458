variable "name" {
  type = string
}

variable "subnet_ids" {
  description = "Isolated subnets in two AZs (an RDS subnet group needs two)."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "An RDS subnet group needs subnets in at least two AZs."
  }
}

variable "security_group_id" {
  type = string
}

variable "availability_zone" {
  description = "Single-AZ placement (AZ A, next to the workloads)."
  type        = string
}

variable "engine_version" {
  type    = string
  default = "8.4"
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "database_name" {
  type    = string
  default = "fashionstore"
}

variable "master_username" {
  type    = string
  default = "fsadmin"
}

variable "allocated_storage_gb" {
  type    = number
  default = 20
}

variable "max_allocated_storage_gb" {
  type    = number
  default = 30
}

variable "backup_retention_days" {
  type    = number
  default = 1
}

variable "skip_final_snapshot" {
  type    = bool
  default = true
}

variable "require_tls" {
  description = "Force TLS for every client. Lambda packages include the regional RDS CA bundle."
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
