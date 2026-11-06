mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name = "fs-test"
}

run "athena_tables_match_report_csv" {
  assert {
    condition     = [for c in aws_glue_catalog_table.this["sales"].storage_descriptor[0].columns : c.name] == ["order_date", "sku", "category", "order_id", "units", "revenue_cents"]
    error_message = "sales columns must match functions/report SALES_COLUMNS"
  }
  assert {
    condition     = [for c in aws_glue_catalog_table.this["stock"].storage_descriptor[0].columns : c.name] == ["sku", "name", "category", "qty", "updated_at"]
    error_message = "stock columns must match functions/report STOCK_COLUMNS"
  }
  assert {
    condition     = aws_glue_catalog_table.this["sales"].parameters["storage.location.template"] == "${aws_glue_catalog_table.this["sales"].storage_descriptor[0].location}dt=$${dt}/" && endswith(aws_glue_catalog_table.this["sales"].storage_descriptor[0].location, "/reports/sales/")
    error_message = "Partition projection path must match the report writer"
  }
  assert {
    condition     = one(aws_s3_bucket_lifecycle_configuration.results.rule).expiration[0].days == 7
    error_message = "Athena results expire after 7 days"
  }
  assert {
    condition     = [for t in one(aws_s3_bucket_lifecycle_configuration.reports.rule).transition : t.storage_class] == ["STANDARD_IA", "GLACIER"] || toset([for t in one(aws_s3_bucket_lifecycle_configuration.reports.rule).transition : t.storage_class]) == toset(["STANDARD_IA", "GLACIER"])
    error_message = "Reports tier to IA then Glacier"
  }
}
