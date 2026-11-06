# Shared mock data for `terraform test` (no AWS credentials or network needed).
mock_data "aws_caller_identity" {
  defaults = {
    account_id = "123456789012"
    arn        = "arn:aws:iam::123456789012:user/test"
  }
}

mock_data "aws_region" {
  defaults = {
    region = "ap-southeast-1"
    name   = "ap-southeast-1"
  }
}

mock_data "aws_partition" {
  defaults = {
    partition = "aws"
  }
}

mock_data "aws_iam_policy_document" {
  defaults = {
    json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
  }
}

mock_data "aws_ec2_managed_prefix_list" {
  defaults = {
    id = "pl-31a34658"
  }
}

mock_data "aws_cloudfront_cache_policy" {
  defaults = {
    id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }
}

mock_data "aws_cloudfront_origin_request_policy" {
  defaults = {
    id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }
}

mock_data "aws_cloudfront_response_headers_policy" {
  defaults = {
    id = "67f7725c-6f97-4210-82d7-5512b31e9d03"
  }
}

mock_resource "aws_eks_cluster" {
  defaults = {
    identity = [{ oidc = [{ issuer = "https://oidc.eks.ap-southeast-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE" }] }]
  }
}

mock_resource "aws_iam_openid_connect_provider" {
  defaults = {
    arn = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.ap-southeast-1.amazonaws.com/id/EXAMPLE"
  }
}

mock_resource "aws_iam_role" {
  defaults = {
    arn = "arn:aws:iam::123456789012:role/mock"
  }
}

mock_resource "aws_lambda_function" {
  defaults = {
    arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:mock"
  }
}

mock_resource "aws_db_instance" {
  defaults = {
    master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:rds!db-mock", kms_key_id = "", secret_status = "active" }]
  }
}

mock_resource "aws_cloudfront_distribution" {
  defaults = {
    arn         = "arn:aws:cloudfront::123456789012:distribution/EMOCK"
    domain_name = "d111111abcdef8.cloudfront.net"
  }
}

mock_resource "aws_cognito_user_pool" {
  defaults = {
    id       = "ap-southeast-1_Mock123"
    endpoint = "cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_Mock123"
  }
}

mock_resource "aws_lb" {
  defaults = {
    arn        = "arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:loadbalancer/app/mock/0123456789abcdef"
    arn_suffix = "app/mock/0123456789abcdef"
    dns_name   = "internal-mock-123.ap-southeast-1.elb.amazonaws.com"
  }
}

mock_resource "aws_lb_target_group" {
  defaults = {
    arn        = "arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:targetgroup/mock/0123456789abcdef"
    arn_suffix = "targetgroup/mock/0123456789abcdef"
  }
}

mock_resource "aws_lb_listener" {
  defaults = {
    arn = "arn:aws:elasticloadbalancing:ap-southeast-1:123456789012:listener/app/mock/0123456789abcdef/0123456789abcdef"
  }
}

mock_resource "aws_sns_topic" {
  defaults = {
    arn = "arn:aws:sns:ap-southeast-1:123456789012:mock"
  }
}

mock_resource "aws_sqs_queue" {
  defaults = {
    arn = "arn:aws:sqs:ap-southeast-1:123456789012:mock"
    id  = "https://sqs.ap-southeast-1.amazonaws.com/123456789012/mock"
  }
}

mock_resource "aws_launch_template" {
  defaults = {
    id             = "lt-0123456789abcdef0"
    latest_version = 1
  }
}

mock_resource "aws_cloudfront_function" {
  defaults = {
    arn = "arn:aws:cloudfront::123456789012:function/mock"
  }
}

mock_resource "aws_cloudfront_vpc_origin" {
  defaults = {
    id  = "vo_mock123"
    arn = "arn:aws:cloudfront::123456789012:vpcorigin/vo_mock123"
  }
}

mock_resource "aws_iam_policy" {
  defaults = {
    arn = "arn:aws:iam::123456789012:policy/mock"
  }
}
