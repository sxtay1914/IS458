output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr" {
  value = aws_vpc.this.cidr_block
}

output "azs" {
  value = var.azs
}

output "public_subnet_ids" {
  description = "L1 public subnets [A, B]."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "L2 private app subnets [A, B]: internal ALB, EKS control plane ENIs."
  value       = aws_subnet.private[*].id
}

output "workload_subnet_ids" {
  description = "AZ A private subnet only: EKS node group and in-VPC Lambdas (Part B runs workloads in AZ A)."
  value       = [aws_subnet.private[0].id]
}

output "isolated_subnet_ids" {
  description = "L3 isolated subnets [A, B]: RDS subnet group."
  value       = aws_subnet.isolated[*].id
}

output "nat_public_ip" {
  value = aws_eip.nat.public_ip
}

output "private_route_table_id" {
  value = aws_route_table.private.id
}

output "security_group_ids" {
  description = "Security groups by role."
  value = {
    alb      = aws_security_group.alb.id
    app      = aws_security_group.app.id
    lambda   = aws_security_group.lambda.id
    database = aws_security_group.database.id
  }
}
