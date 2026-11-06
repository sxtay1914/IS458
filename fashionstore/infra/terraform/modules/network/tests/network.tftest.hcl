mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name             = "fs-test"
  azs              = ["ap-southeast-1a", "ap-southeast-1b"]
  eks_cluster_name = "fs-test-eks"
}

run "three_layers_two_azs" {
  assert {
    condition     = aws_vpc.this.cidr_block == "10.10.0.0/16"
    error_message = "VPC CIDR must be 10.10.0.0/16"
  }
  assert {
    condition     = [for s in aws_subnet.public : s.cidr_block] == ["10.10.1.0/24", "10.10.2.0/24"]
    error_message = "L1 public CIDRs wrong"
  }
  assert {
    condition     = [for s in aws_subnet.private : s.cidr_block] == ["10.10.3.0/24", "10.10.4.0/24"]
    error_message = "L2 private CIDRs wrong"
  }
  assert {
    condition     = [for s in aws_subnet.isolated : s.cidr_block] == ["10.10.5.0/24", "10.10.6.0/24"]
    error_message = "L3 isolated CIDRs wrong"
  }
  assert {
    condition     = alltrue([for s in aws_subnet.public : s.map_public_ip_on_launch == false])
    error_message = "No subnet may auto-assign public IPs"
  }
  assert {
    condition     = alltrue([for s in aws_subnet.private : s.tags["kubernetes.io/role/internal-elb"] == "1"])
    error_message = "Private subnets need the internal-elb tag"
  }
}

run "one_nat_in_az_a_and_isolated_has_no_internet" {
  assert {
    condition     = aws_nat_gateway.this.subnet_id == aws_subnet.public[0].id
    error_message = "The single NAT must sit in AZ A's public subnet"
  }
  assert {
    condition     = aws_route.private_nat.route_table_id == aws_route_table.private.id && aws_route.public_internet.route_table_id == aws_route_table.public.id
    error_message = "Only the public and private route tables get default routes"
  }
  assert {
    condition     = length(aws_route_table.isolated.route) == 0
    error_message = "Isolated route table must have no routes besides local"
  }
  assert {
    condition     = output.workload_subnet_ids == [aws_subnet.private[0].id]
    error_message = "Workloads run in AZ A only"
  }
}

run "s3_gateway_endpoint_is_free_type" {
  assert {
    condition     = aws_vpc_endpoint.s3.vpc_endpoint_type == "Gateway"
    error_message = "S3 endpoint must be a (free) gateway endpoint"
  }
  assert {
    condition     = toset(aws_vpc_endpoint.s3.route_table_ids) == toset([aws_route_table.private.id, aws_route_table.isolated.id])
    error_message = "S3 endpoint must attach to private and isolated route tables"
  }
}

run "security_groups_are_least_privilege" {
  assert {
    condition     = aws_vpc_security_group_ingress_rule.alb_from_cloudfront.prefix_list_id == "pl-31a34658" && aws_vpc_security_group_ingress_rule.alb_from_cloudfront.from_port == 80
    error_message = "ALB must only accept CloudFront origin-facing traffic on 80"
  }
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.alb_from_extra) == 0
    error_message = "No extra ALB sources by default"
  }
  assert {
    condition = toset([
      aws_vpc_security_group_ingress_rule.db_from_app.referenced_security_group_id,
      aws_vpc_security_group_ingress_rule.db_from_lambda.referenced_security_group_id,
    ]) == toset([aws_security_group.app.id, aws_security_group.lambda.id])
    error_message = "RDS accepts only app and lambda SGs"
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.db_from_app.from_port == 3306 && aws_vpc_security_group_ingress_rule.db_from_lambda.to_port == 3306
    error_message = "RDS ingress is MySQL only"
  }
  assert {
    condition     = aws_vpc_security_group_egress_rule.alb_to_app.referenced_security_group_id == aws_security_group.app.id && aws_vpc_security_group_egress_rule.alb_to_app.from_port == 8080
    error_message = "ALB egress only to app pods on 8080"
  }
}

run "extra_alb_source_for_vpc_origin_service_sg" {
  variables {
    alb_extra_source_security_group_ids = ["sg-0cfvpcorigin"]
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.alb_from_extra["sg-0cfvpcorigin"].referenced_security_group_id == "sg-0cfvpcorigin"
    error_message = "Extra source SG not applied"
  }
}

run "rejects_three_azs" {
  command = plan
  variables {
    azs = ["ap-southeast-1a", "ap-southeast-1b", "ap-southeast-1c"]
  }
  expect_failures = [var.azs]
}
