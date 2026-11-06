variable "name" {
  description = "Name prefix, for example fashionstore-demo."
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block."
  type        = string
  default     = "10.10.0.0/16"
}

variable "azs" {
  description = "Exactly two availability zones. Index 0 (AZ A) runs all workloads; AZ B holds subnets only, so the ALB, RDS subnet group and EKS control plane are valid."
  type        = list(string)

  validation {
    condition     = length(var.azs) == 2
    error_message = "Give exactly two availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "L1 public web subnets, one per AZ."
  type        = list(string)
  default     = ["10.10.1.0/24", "10.10.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "L2 private app subnets, one per AZ (EKS nodes, internal ALB, in-VPC Lambdas)."
  type        = list(string)
  default     = ["10.10.3.0/24", "10.10.4.0/24"]
}

variable "isolated_subnet_cidrs" {
  description = "L3 isolated database subnets, one per AZ. No route to the internet."
  type        = list(string)
  default     = ["10.10.5.0/24", "10.10.6.0/24"]
}

variable "eks_cluster_name" {
  description = "EKS cluster name, used for the kubernetes.io/cluster subnet tag."
  type        = string
}

variable "app_port" {
  description = "Container port store-api listens on (ALB target port)."
  type        = number
  default     = 8080
}

variable "alb_listener_port" {
  description = "Port the internal ALB listens on. CloudFront reaches it over HTTP through the VPC origin."
  type        = number
  default     = 80
}

variable "alb_extra_source_security_group_ids" {
  description = "Extra security groups allowed into the ALB, for example CloudFront-VPCOrigins-Service-SG if the VPC origin connects from it rather than the prefix list."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Extra tags for every resource."
  type        = map(string)
  default     = {}
}
