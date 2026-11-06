mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name                  = "fs-test"
  region                = "ap-southeast-1"
  vpc_id                = "vpc-1"
  alb_subnet_ids        = ["subnet-a", "subnet-b"]
  alb_security_group_id = "sg-alb"
}

run "alb_is_internal_with_weighted_pilot" {
  assert {
    condition     = aws_lb.api.internal == true
    error_message = "ALB must be internal (VPC origin)"
  }
  assert {
    condition     = sort([for tg in aws_lb_listener_rule.api.action[0].forward[0].target_group : format("%03d", tg.weight)]) == tolist(["010", "090"])
    error_message = "v1/v2 weights must default to 90/10"
  }
  assert {
    condition     = alltrue([for tg in aws_lb_target_group.api : tg.target_type == "ip" && tg.port == 8080])
    error_message = "Target groups take pod IPs on 8080"
  }
  assert {
    condition     = one(aws_lb_listener_rule.api.condition).path_pattern[0].values == toset(["/api/*"])
    error_message = "Only /api/* is forwarded"
  }
}

run "cloudfront_uses_vpc_origin_and_oac" {
  assert {
    condition     = aws_cloudfront_vpc_origin.api.vpc_origin_endpoint_config[0].origin_protocol_policy == "http-only"
    error_message = "VPC origin speaks HTTP to the internal ALB"
  }
  assert {
    condition     = length([for o in aws_cloudfront_distribution.this.origin : o if length(o.vpc_origin_config) == 1]) == 1
    error_message = "API origin must use vpc_origin_config"
  }
  assert {
    condition     = length([for o in aws_cloudfront_distribution.this.origin : o if o.origin_access_control_id != null && o.origin_access_control_id != ""]) == 1
    error_message = "S3 origin must use OAC"
  }
  assert {
    condition     = aws_cloudfront_distribution.this.ordered_cache_behavior[0].path_pattern == "/api/*" && aws_cloudfront_distribution.this.ordered_cache_behavior[0].viewer_protocol_policy == "https-only"
    error_message = "/api/* is HTTPS-only"
  }
  assert {
    condition     = aws_cloudfront_distribution.this.default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https"
    error_message = "Storefront redirects to HTTPS"
  }
  assert {
    condition     = length(aws_cloudfront_distribution.this.custom_error_response) == 0
    error_message = "No distribution-wide error rewrites (would hide API 404s)"
  }
}

run "pilot_shift" {
  variables {
    v1_weight = 0
    v2_weight = 100
  }
  assert {
    condition     = sort([for tg in aws_lb_listener_rule.api.action[0].forward[0].target_group : format("%03d", tg.weight)]) == tolist(["000", "100"])
    error_message = "Weights must follow variables"
  }
}

run "rejects_weight_over_999" {
  command = plan
  variables {
    v2_weight = 1000
  }
  expect_failures = [var.v2_weight]
}
