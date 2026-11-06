output "reports_bucket" {
  value = module.reports_bucket.id
}

output "reports_bucket_arn" {
  value = module.reports_bucket.arn
}

output "athena_results_bucket" {
  value = module.results_bucket.id
}

output "athena_workgroup" {
  value = aws_athena_workgroup.this.name
}

output "glue_database" {
  value = aws_glue_catalog_database.this.name
}

output "glue_tables" {
  value = [for t in aws_glue_catalog_table.this : t.name]
}
