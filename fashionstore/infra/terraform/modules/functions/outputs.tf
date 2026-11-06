output "function_names" {
  value = { for k, f in aws_lambda_function.this : k => f.function_name }
}

output "function_arns" {
  value = { for k, f in aws_lambda_function.this : k => f.arn }
}

output "role_arns" {
  value = { for k, r in aws_iam_role.this : k => r.arn }
}

output "ses_identities" {
  value = [for i in aws_sesv2_email_identity.this : i.email_identity]
}
