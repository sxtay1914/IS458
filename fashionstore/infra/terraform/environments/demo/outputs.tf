output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "workload_subnet_ids" {
  value = module.network.workload_subnet_ids
}

output "isolated_subnet_ids" {
  value = module.network.isolated_subnet_ids
}

output "security_group_ids" {
  value = module.network.security_group_ids
}

output "nat_public_ip" {
  value = module.network.nat_public_ip
}

output "eks_cluster_name" {
  description = "Name the eks module must use (subnets are already tagged with it)."
  value       = local.eks_cluster_name
}
