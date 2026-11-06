# Simple analytics kept in Part B: report Lambda -> S3 CSVs -> Athena.
# The schedule and the Lambda live in the functions module (event bindings).

data "aws_caller_identity" "current" {}

module "reports_bucket" {
  source        = "../private-bucket"
  bucket        = "${var.name}-reports-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.force_destroy
  tags          = var.tags
}

module "results_bucket" {
  source        = "../private-bucket"
  bucket        = "${var.name}-athena-results-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.force_destroy
  tags          = var.tags
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = module.reports_bucket.id

  rule {
    id     = "reports-tiering"
    status = "Enabled"
    filter {
      prefix = "reports/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = var.reports_expire_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "results" {
  bucket = module.results_bucket.id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"
    filter {}

    expiration {
      days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_athena_workgroup" "this" {
  name          = "${var.name}-reports"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 104857600 # 100 MB guardrail

    result_configuration {
      output_location = "s3://${module.results_bucket.id}/results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = var.tags
}

resource "aws_glue_catalog_database" "this" {
  name        = replace("${var.name}_reports", "-", "_")
  description = "FashionStore daily sales and stock reports (CSV)"
}

locals {
  # Partition projection on dt: new days are queryable without a crawler.
  csv_table_parameters = {
    "classification"              = "csv"
    "skip.header.line.count"      = "1"
    "projection.enabled"          = "true"
    "projection.dt.type"          = "date"
    "projection.dt.format"        = "yyyy-MM-dd"
    "projection.dt.range"         = "2026-01-01,NOW"
    "projection.dt.interval"      = "1"
    "projection.dt.interval.unit" = "DAYS"
  }

  # Column order must match functions/report/handler.py SALES_COLUMNS / STOCK_COLUMNS.
  table_columns = {
    sales = ["order_date", "sku", "category", "order_id", "units", "revenue_cents"]
    stock = ["sku", "name", "category", "qty", "updated_at"]
  }
}

resource "aws_glue_catalog_table" "this" {
  for_each = local.table_columns

  name          = each.key
  database_name = aws_glue_catalog_database.this.name
  table_type    = "EXTERNAL_TABLE"

  parameters = merge(local.csv_table_parameters, {
    "storage.location.template" = "s3://${module.reports_bucket.id}/reports/${each.key}/dt=$${dt}/"
  })

  partition_keys {
    name = "dt"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${module.reports_bucket.id}/reports/${each.key}/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters = {
        "separatorChar" = ","
        "quoteChar"     = "\""
      }
    }

    dynamic "columns" {
      for_each = each.value
      content {
        name = columns.value
        # OpenCSVSerde reads every column as a string; queries CAST on read.
        type = "string"
      }
    }
  }
}

resource "aws_athena_named_query" "daily_revenue" {
  name      = "daily-revenue"
  workgroup = aws_athena_workgroup.this.name
  database  = aws_glue_catalog_database.this.name
  query     = <<-SQL
    SELECT dt,
           COUNT(DISTINCT order_id)                  AS orders,
           SUM(CAST(revenue_cents AS bigint)) / 100.0 AS revenue_sgd
    FROM sales
    WHERE dt >= date_format(current_date - interval '7' day, '%Y-%m-%d')
    GROUP BY dt
    ORDER BY dt DESC
  SQL
}

resource "aws_athena_named_query" "low_stock" {
  name      = "low-stock"
  workgroup = aws_athena_workgroup.this.name
  database  = aws_glue_catalog_database.this.name
  query     = <<-SQL
    SELECT sku, name, CAST(qty AS integer) AS qty
    FROM stock
    WHERE dt = (SELECT max(dt) FROM stock) AND CAST(qty AS integer) < 10
    ORDER BY 3
  SQL
}
