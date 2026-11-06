locals {
  name             = "${var.project}-${var.environment}"
  eks_cluster_name = "${local.name}-eks"

  tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ExpiresOn   = var.expires_on
    ManagedBy   = "terraform"
  }
}

# Phase 1: network. Later phases add, in this order:
#   registry, database, eks, observability   (Day 1)
#   messaging, functions                      (Day 1-2)
#   delivery (ALB half)                       (Day 2)
#   identity, delivery (edge half)            (Day 3)
#   analytics                                 (Day 4)
# See docs/implementation-plan.md.

module "network" {
  source = "../../modules/network"

  name             = local.name
  vpc_cidr         = var.vpc_cidr
  azs              = var.azs
  eks_cluster_name = local.eks_cluster_name

  alb_extra_source_security_group_ids = var.alb_extra_source_security_group_ids
}
