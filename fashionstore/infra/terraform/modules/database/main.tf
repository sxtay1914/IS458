resource "aws_db_subnet_group" "this" {
  name        = "${var.name}-db"
  description = "L3 isolated subnets (no internet route)"
  subnet_ids  = var.subnet_ids
  tags        = merge(var.tags, { Name = "${var.name}-db" })
}

resource "aws_db_parameter_group" "this" {
  name        = "${var.name}-mysql84"
  family      = "mysql8.4"
  description = "FashionStore MySQL 8.4"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_0900_ai_ci"
  }

  parameter {
    name  = "time_zone"
    value = "UTC"
  }

  # Lock waits fail fast so a stuck checkout is retried rather than holding a worker.
  parameter {
    name  = "innodb_lock_wait_timeout"
    value = "10"
  }

  parameter {
    name  = "require_secure_transport"
    value = var.require_tls ? "1" : "0"
  }

  tags = var.tags
}

resource "aws_db_instance" "this" {
  identifier               = "${var.name}-mysql"
  engine                   = "mysql"
  engine_version           = var.engine_version
  engine_lifecycle_support = "open-source-rds-extended-support-disabled"
  instance_class           = var.instance_class

  db_name                     = var.database_name
  username                    = var.master_username
  manage_master_user_password = true

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  parameter_group_name   = aws_db_parameter_group.this.name
  vpc_security_group_ids = [var.security_group_id]
  availability_zone      = var.availability_zone
  multi_az               = false
  publicly_accessible    = false

  backup_retention_period    = var.backup_retention_days
  backup_window              = "18:00-18:30"
  maintenance_window         = "sun:19:00-sun:19:30"
  auto_minor_version_upgrade = true
  apply_immediately          = true

  deletion_protection       = false
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.name}-mysql-final"
  delete_automated_backups  = true
  copy_tags_to_snapshot     = true

  performance_insights_enabled    = false
  enabled_cloudwatch_logs_exports = ["error", "slowquery"]

  tags = merge(var.tags, { Name = "${var.name}-mysql" })
}
