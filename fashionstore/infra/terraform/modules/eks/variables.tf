variable "name" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "kubernetes_version" {
  type    = string
  default = "1.34"
}

variable "control_plane_subnet_ids" {
  description = "Private subnets in two AZs for the control-plane ENIs."
  type        = list(string)
}

variable "node_subnet_ids" {
  description = "Node group subnets (AZ A only in Part B)."
  type        = list(string)
}

variable "node_security_group_id" {
  description = "The network module's app SG (ALB -> pods, pods -> RDS)."
  type        = string
}

variable "public_access_cidrs" {
  description = "Who may reach the public Kubernetes API endpoint. Narrow this to your team's IPs."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "admin_principal_arns" {
  description = "Extra IAM principals (team members, CI apply role) granted cluster admin. The creator is admin automatically."
  type        = list(string)
  default     = []
}

variable "node_instance_type" {
  type    = string
  default = "t3.small"
}

variable "node_capacity_type" {
  type    = string
  default = "ON_DEMAND"
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 3
}

variable "app_namespace" {
  type    = string
  default = "fashionstore"
}

variable "checkout_queue_arn" {
  type = string
}

variable "checkout_status_topic_arn" {
  type = string
}

variable "db_secret_arn" {
  type = string
}

variable "target_group_arns" {
  description = "Target groups the LB controller may register pod IPs into (v1, v2)."
  type        = list(string)
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "tags" {
  type    = map(string)
  default = {}
}
