output "vpc_id" {
  value = module.network.vpc_id
}

output "storefront_url" {
  value = "https://${module.delivery.cloudfront_domain_name}"
}

output "cloudfront_distribution_id" {
  value = module.delivery.cloudfront_distribution_id
}

output "storefront_bucket" {
  value = module.delivery.storefront_bucket
}

output "alb_dns_name" {
  value = module.delivery.alb_dns_name
}

output "target_group_arns" {
  description = "Put these in the TargetGroupBinding manifests (v1, v2)."
  value       = module.delivery.target_group_arns
}

output "ecr_repository_urls" {
  value = module.registry.repository_urls
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "irsa_role_arns" {
  value = module.eks.irsa_role_arns
}

output "db_address" {
  value = module.database.address
}

output "db_secret_arn" {
  value = module.database.master_secret_arn
}

output "checkout_queue_url" {
  value = module.messaging.checkout_queue_url
}

output "checkout_dlq_url" {
  value = module.messaging.checkout_dlq_url
}

output "checkout_status_topic_arn" {
  value = module.messaging.checkout_status_topic_arn
}

output "function_names" {
  value = module.functions.function_names
}

output "cognito" {
  value = {
    user_pool_id = module.identity.user_pool_id
    client_id    = module.identity.client_id
    issuer_url   = module.identity.issuer_url
    domain       = module.identity.hosted_ui_domain
  }
}

output "reports" {
  value = {
    bucket    = module.analytics.reports_bucket
    workgroup = module.analytics.athena_workgroup
    database  = module.analytics.glue_database
  }
}

output "dashboard_name" {
  value = module.observability.dashboard_name
}

# Single source for application settings (store-api ConfigMap, storefront .env).
output "app_config" {
  value = {
    AWS_REGION                = var.region
    DB_HOST                   = module.database.address
    DB_NAME                   = module.database.database_name
    DB_SECRET_ARN             = module.database.master_secret_arn
    CHECKOUT_QUEUE_URL        = module.messaging.checkout_queue_url
    CHECKOUT_STATUS_TOPIC_ARN = module.messaging.checkout_status_topic_arn
    COGNITO_ISSUER_URL        = module.identity.issuer_url
    COGNITO_CLIENT_ID         = module.identity.client_id
    COGNITO_DOMAIN            = module.identity.hosted_ui_domain
    STOREFRONT_URL            = "https://${module.delivery.cloudfront_domain_name}"
  }
}
