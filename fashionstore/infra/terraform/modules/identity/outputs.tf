output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  value = aws_cognito_user_pool.this.arn
}

output "issuer_url" {
  description = "JWT issuer; store-api validates tokens against <issuer>/.well-known/jwks.json."
  value       = "https://${aws_cognito_user_pool.this.endpoint}"
}

output "client_id" {
  value = aws_cognito_user_pool_client.storefront.id
}

output "hosted_ui_domain" {
  value = "${aws_cognito_user_pool_domain.this.domain}.auth.${split("_", aws_cognito_user_pool.this.id)[0]}.amazoncognito.com"
}
