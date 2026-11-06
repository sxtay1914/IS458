# Shoppers -> CloudFront
#   default      -> private S3 storefront (Origin Access Control)
#   /api/*       -> CloudFront VPC origin -> internal ALB (L2) -> weighted v1/v2 target groups
#
# Nothing in the VPC is internet-facing: the ALB is internal and only accepts
# CloudFront origin-facing traffic (network module SG).

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# Internal ALB and the v1 / v2 pilot split
# ---------------------------------------------------------------------------

resource "aws_lb" "api" {
  name               = "${var.name}-api"
  internal           = true
  load_balancer_type = "application"
  subnets            = var.alb_subnet_ids
  security_groups    = [var.alb_security_group_id]
  idle_timeout       = 30

  drop_invalid_header_fields = true
  enable_deletion_protection = false

  tags = merge(var.tags, { Name = "${var.name}-api" })
}

resource "aws_lb_target_group" "api" {
  for_each = toset(["v1", "v2"])

  name                 = "${var.name}-api-${each.key}"
  port                 = var.app_port
  protocol             = "HTTP"
  target_type          = "ip" # pod IPs, registered by TargetGroupBinding
  vpc_id               = var.vpc_id
  deregistration_delay = 15

  health_check {
    path                = var.health_check_path
    matcher             = "200"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = merge(var.tags, { Name = "${var.name}-api-${each.key}", Version = each.key })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "application/json"
      message_body = "{\"error\":\"not_found\"}"
      status_code  = "404"
    }
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }

  action {
    type = "forward"
    forward {
      target_group {
        arn    = aws_lb_target_group.api["v1"].arn
        weight = var.v1_weight
      }
      target_group {
        arn    = aws_lb_target_group.api["v2"].arn
        weight = var.v2_weight
      }
      # No stickiness: every request is split independently, which keeps the
      # measured split close to the configured weights.
      stickiness {
        enabled  = false
        duration = 1
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Storefront bucket (private) + CloudFront
# ---------------------------------------------------------------------------

module "storefront_bucket" {
  source        = "../private-bucket"
  bucket        = "${var.name}-storefront-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = var.tags

  extra_policy_statements = [{
    Sid       = "AllowCloudFrontOAC"
    Effect    = "Allow"
    Principal = { Service = "cloudfront.amazonaws.com" }
    Action    = "s3:GetObject"
    Resource  = "arn:aws:s3:::${var.name}-storefront-${data.aws_caller_identity.current.account_id}/*"
    Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.this.arn } }
  }]
}

resource "aws_cloudfront_origin_access_control" "storefront" {
  name                              = "${var.name}-storefront"
  description                       = "OAC for the private storefront bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_vpc_origin" "api" {
  vpc_origin_endpoint_config {
    name                   = "${var.name}-api"
    arn                    = aws_lb.api.arn
    http_port              = 80
    https_port             = 443
    origin_protocol_policy = "http-only"

    origin_ssl_protocols {
      items    = ["TLSv1.2"]
      quantity = 1
    }
  }

  tags = var.tags
}

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

data "aws_cloudfront_response_headers_policy" "security_headers" {
  name = "Managed-SecurityHeadersPolicy"
}

# SPA routing: rewrite extension-less paths to /index.html on the S3 behaviour
# only. A distribution-wide custom error response would also swallow API 404s.
resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "${var.name}-spa-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Serve index.html for client-side routes"
  publish = true
  code    = file("${path.module}/spa-rewrite.js")
}

locals {
  s3_origin_id  = "storefront-s3"
  api_origin_id = "api-alb"
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.name} storefront + API"
  default_root_object = "index.html"
  price_class         = var.price_class
  http_version        = "http2and3"

  origin {
    origin_id                = local.s3_origin_id
    domain_name              = "${var.name}-storefront-${data.aws_caller_identity.current.account_id}.s3.${var.region}.amazonaws.com"
    origin_access_control_id = aws_cloudfront_origin_access_control.storefront.id
  }

  origin {
    origin_id   = local.api_origin_id
    domain_name = aws_lb.api.dns_name

    vpc_origin_config {
      vpc_origin_id            = aws_cloudfront_vpc_origin.api.id
      origin_keepalive_timeout = 5
      origin_read_timeout      = 30
    }
  }

  default_cache_behavior {
    target_origin_id           = local.s3_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimized.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security_headers.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = local.api_origin_id
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = true
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = var.tags
}
