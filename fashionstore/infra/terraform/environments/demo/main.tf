locals {
  name             = "${var.project}-${var.environment}"
  eks_cluster_name = "${local.name}-eks"
  packages_dir     = coalesce(var.packages_dir, abspath("${path.root}/../../../../build/functions"))

  tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ExpiresOn   = var.expires_on
    ManagedBy   = "terraform"
  }
}

# --- Day 1: foundation ------------------------------------------------------

module "network" {
  source = "../../modules/network"

  name             = local.name
  vpc_cidr         = var.vpc_cidr
  azs              = var.azs
  eks_cluster_name = local.eks_cluster_name

  alb_extra_source_security_group_ids = var.alb_extra_source_security_group_ids
}

module "registry" {
  source = "../../modules/registry"
  name   = local.name
}

module "database" {
  source = "../../modules/database"

  name              = local.name
  subnet_ids        = module.network.isolated_subnet_ids
  security_group_id = module.network.security_group_ids.database
  availability_zone = var.azs[0]
}

# --- Day 1-2: checkout pipeline ----------------------------------------------

module "messaging" {
  source = "../../modules/messaging"

  name             = local.name
  ops_alert_emails = var.ops_alert_emails
}

module "analytics" {
  source = "../../modules/analytics"
  name   = local.name
}

module "functions" {
  source = "../../modules/functions"

  name              = local.name
  packages_dir      = local.packages_dir
  subnet_ids        = module.network.workload_subnet_ids
  security_group_id = module.network.security_group_ids.lambda

  db_host       = module.database.address
  db_port       = module.database.port
  db_name       = module.database.database_name
  db_secret_arn = module.database.master_secret_arn

  checkout_queue_arn         = module.messaging.checkout_queue_arn
  checkout_status_topic_arn  = module.messaging.checkout_status_topic_arn
  notifier_failure_queue_arn = module.messaging.notifier_failures_queue_arn

  reports_bucket     = module.analytics.reports_bucket
  reports_bucket_arn = module.analytics.reports_bucket_arn

  sender_email         = var.sender_email
  ses_recipient_emails = var.ses_recipient_emails

  process_checkout_reserved_concurrency = 5
  reserve_checkout_concurrency          = false # Account quota is 10; SQS still caps workers at 5.
  payment_decline_percent               = var.payment_decline_percent
}

# --- Day 2-3: API on EKS, edge, identity --------------------------------------

module "delivery" {
  source = "../../modules/delivery"

  name                  = local.name
  region                = var.region
  vpc_id                = module.network.vpc_id
  alb_subnet_ids        = module.network.private_subnet_ids
  alb_security_group_id = module.network.security_group_ids.alb
  v1_weight             = var.v1_weight
  v2_weight             = var.v2_weight
}

module "eks" {
  source = "../../modules/eks"

  name                     = local.name
  cluster_name             = local.eks_cluster_name
  control_plane_subnet_ids = module.network.private_subnet_ids
  node_subnet_ids          = module.network.workload_subnet_ids
  node_security_group_id   = module.network.security_group_ids.app
  public_access_cidrs      = var.eks_public_access_cidrs
  admin_principal_arns     = var.eks_admin_principal_arns

  node_instance_type = "t3.medium"
  node_min_size      = 1
  node_desired_size  = 2
  node_max_size      = 3

  checkout_queue_arn        = module.messaging.checkout_queue_arn
  checkout_status_topic_arn = module.messaging.checkout_status_topic_arn
  db_secret_arn             = module.database.master_secret_arn
  target_group_arns         = values(module.delivery.target_group_arns)
}

module "identity" {
  source = "../../modules/identity"

  name = local.name
  callback_urls = [
    "https://${module.delivery.cloudfront_domain_name}/auth/callback",
    "http://localhost:5173/auth/callback",
  ]
  logout_urls = [
    "https://${module.delivery.cloudfront_domain_name}/",
    "http://localhost:5173/",
  ]
}

# --- Day 4: operate ------------------------------------------------------------

module "observability" {
  source = "../../modules/observability"

  name                         = local.name
  ops_alerts_topic_arn         = module.messaging.ops_alerts_topic_arn
  checkout_queue_name          = module.messaging.checkout_queue_name
  checkout_dlq_name            = module.messaging.checkout_dlq_name
  notifier_failures_queue_name = module.messaging.notifier_failures_queue_name
  function_names               = module.functions.function_names
  db_instance_id               = module.database.instance_id
  alb_arn_suffix               = module.delivery.alb_arn_suffix
  target_group_arn_suffixes    = module.delivery.target_group_arn_suffixes
}
