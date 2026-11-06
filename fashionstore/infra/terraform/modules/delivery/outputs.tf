output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.this.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.this.id
}

output "storefront_bucket" {
  value = module.storefront_bucket.id
}

output "alb_arn" {
  value = aws_lb.api.arn
}

output "alb_arn_suffix" {
  value = aws_lb.api.arn_suffix
}

output "alb_dns_name" {
  description = "Internal only: resolves to private IPs."
  value       = aws_lb.api.dns_name
}

output "target_group_arns" {
  value = { for k, tg in aws_lb_target_group.api : k => tg.arn }
}

output "target_group_arn_suffixes" {
  value = { for k, tg in aws_lb_target_group.api : k => tg.arn_suffix }
}
