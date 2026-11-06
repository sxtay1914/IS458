# Cognito user pool + hosted domain + public SPA client (authorization code + PKCE).

data "aws_caller_identity" "current" {}

resource "aws_cognito_user_pool" "this" {
  name                     = "${var.name}-shoppers"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = "INACTIVE"
  mfa_configuration        = "OFF"

  password_policy {
    minimum_length                   = 10
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 3
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  # Cognito's built-in sender: 50 emails/day, enough for a demo.
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 5
      max_length = 254
    }
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_domain" "this" {
  # Globally unique prefix; the account id keeps two teams from colliding.
  domain       = "${var.name}-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.this.id

  # Classic hosted UI: stable form field names that scripts/get-test-token.mjs
  # fills in a headless browser to get real PKCE tokens for the live tests.
  managed_login_version = 1
}

resource "aws_cognito_resource_server" "api" {
  identifier   = "fashionstore-api"
  name         = "FashionStore API"
  user_pool_id = aws_cognito_user_pool.this.id

  scope {
    scope_name        = "orders.read"
    scope_description = "Read own orders"
  }

  scope {
    scope_name        = "checkout.write"
    scope_description = "Place checkouts and manage own cart"
  }
}

resource "aws_cognito_user_pool_client" "storefront" {
  name         = "${var.name}-storefront"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false # public SPA client: PKCE, no secret
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes = concat(
    ["openid", "email", "profile"],
    [for s in aws_cognito_resource_server.api.scope_identifiers : s],
  )
  supported_identity_providers = ["COGNITO"]
  callback_urls                = var.callback_urls
  logout_urls                  = var.logout_urls

  # No ALLOW_USER_PASSWORD_AUTH: Cognito puts only aws.cognito.signin.user.admin
  # in those access tokens, never the fashionstore-api/* scopes the API needs.
  # Scripted tests sign in through the hosted UI instead (code + PKCE).
  explicit_auth_flows = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]

  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 7

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}
