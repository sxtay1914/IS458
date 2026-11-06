mock_provider "aws" {
  source = "../../tests/mocks"
}

# scope_identifiers is computed; give the mock what AWS returns.
override_resource {
  target = aws_cognito_resource_server.api
  values = {
    scope_identifiers = ["fashionstore-api/orders.read", "fashionstore-api/checkout.write"]
  }
}

variables {
  name          = "fs-test"
  callback_urls = ["https://d111111abcdef8.cloudfront.net/auth/callback"]
  logout_urls   = ["https://d111111abcdef8.cloudfront.net/"]
}

run "spa_client_uses_pkce_code_flow" {
  assert {
    condition     = aws_cognito_user_pool_client.storefront.generate_secret == false
    error_message = "Public SPA client must not have a secret"
  }
  assert {
    condition     = aws_cognito_user_pool_client.storefront.allowed_oauth_flows == toset(["code"])
    error_message = "Only the authorization code flow (PKCE)"
  }
  assert {
    condition     = !contains(aws_cognito_user_pool_client.storefront.explicit_auth_flows, "ALLOW_USER_PASSWORD_AUTH")
    error_message = "Password-auth tokens lack the API scopes; tests use the hosted UI instead"
  }
  assert {
    condition     = contains(aws_cognito_user_pool_client.storefront.allowed_oauth_scopes, "fashionstore-api/checkout.write") && contains(aws_cognito_user_pool_client.storefront.allowed_oauth_scopes, "fashionstore-api/orders.read")
    error_message = "SPA client must be allowed both API scopes"
  }
}

run "hosted_ui_is_classic_for_scripted_sign_in" {
  assert {
    condition     = aws_cognito_user_pool_domain.this.managed_login_version == 1
    error_message = "get-test-token.mjs expects the classic hosted UI"
  }
}
