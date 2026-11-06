mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name                      = "fs-test"
  cluster_name              = "fs-test-eks"
  control_plane_subnet_ids  = ["subnet-a", "subnet-b"]
  node_subnet_ids           = ["subnet-a"]
  node_security_group_id    = "sg-app"
  checkout_queue_arn        = "arn:aws:sqs:ap-southeast-1:123456789012:q"
  checkout_status_topic_arn = "arn:aws:sns:ap-southeast-1:123456789012:t"
  db_secret_arn             = "arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:db"
  target_group_arns         = ["arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:targetgroup/v1/1", "arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:targetgroup/v2/2"]
}

run "node_group_sizing" {
  assert {
    condition     = aws_eks_cluster.this.version == "1.34" && aws_eks_cluster.this.upgrade_policy[0].support_type == "STANDARD"
    error_message = "Use standard-support Kubernetes and disable paid extended support"
  }
  assert {
    condition     = tolist(aws_eks_node_group.this.instance_types) == tolist(["t3.small"])
    error_message = "Nodes must be t3.small"
  }
  assert {
    condition     = aws_eks_node_group.this.scaling_config[0].min_size == 1 && aws_eks_node_group.this.scaling_config[0].desired_size == 2 && aws_eks_node_group.this.scaling_config[0].max_size == 3
    error_message = "ASG must be 1 / 2 / 3"
  }
  assert {
    condition     = aws_eks_node_group.this.subnet_ids == toset(["subnet-a"])
    error_message = "Nodes run in AZ A only"
  }
}

run "nodes_carry_app_and_cluster_sgs" {
  assert {
    condition     = toset(aws_launch_template.node.vpc_security_group_ids) == toset([aws_eks_cluster.this.vpc_config[0].cluster_security_group_id, "sg-app"])
    error_message = "Launch template must keep the cluster SG and add the app SG"
  }
  assert {
    condition     = aws_launch_template.node.metadata_options[0].http_tokens == "required"
    error_message = "IMDSv2 only"
  }
}

run "irsa_roles_are_scoped_to_service_accounts" {
  assert {
    condition     = toset(keys(aws_iam_role.irsa)) == toset(["store-api", "cluster-autoscaler", "aws-load-balancer-controller"])
    error_message = "Expected three IRSA roles"
  }
  assert {
    condition     = aws_eks_cluster.this.access_config[0].authentication_mode == "API"
    error_message = "Use EKS access entries (API mode)"
  }
}
