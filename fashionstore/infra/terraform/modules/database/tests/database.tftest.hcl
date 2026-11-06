mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name              = "fs-test"
  subnet_ids        = ["subnet-iso-a", "subnet-iso-b"]
  security_group_id = "sg-db"
  availability_zone = "ap-southeast-1a"
}

run "single_az_micro_private" {
  assert {
    condition     = aws_db_instance.this.engine_version == "8.4" && aws_db_parameter_group.this.family == "mysql8.4" && aws_db_instance.this.engine_lifecycle_support == "open-source-rds-extended-support-disabled"
    error_message = "Use MySQL 8.4 without paid extended support"
  }
  assert {
    condition     = anytrue([for p in aws_db_parameter_group.this.parameter : p.name == "require_secure_transport" && p.value == "1"])
    error_message = "Database clients must use TLS"
  }
  assert {
    condition     = aws_db_instance.this.instance_class == "db.t4g.micro" && aws_db_instance.this.multi_az == false
    error_message = "Part B uses single-AZ db.t4g.micro"
  }
  assert {
    condition     = aws_db_instance.this.publicly_accessible == false && aws_db_instance.this.storage_encrypted
    error_message = "RDS must be private and encrypted"
  }
  assert {
    condition     = aws_db_instance.this.manage_master_user_password == true && aws_db_instance.this.password == null
    error_message = "Password must be RDS-managed in Secrets Manager"
  }
  assert {
    condition     = aws_db_instance.this.availability_zone == "ap-southeast-1a"
    error_message = "RDS sits next to the workloads in AZ A"
  }
  assert {
    condition     = aws_db_instance.this.skip_final_snapshot && aws_db_instance.this.deletion_protection == false
    error_message = "Demo stack must destroy cleanly"
  }
  assert {
    condition     = output.master_secret_arn != ""
    error_message = "Secret ARN must be exported"
  }
}

run "needs_two_subnets" {
  command = plan
  variables {
    subnet_ids = ["subnet-iso-a"]
  }
  expect_failures = [var.subnet_ids]
}
