package com.fashionstore.auth;

import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.Jwt;

/** Cognito access tokens carry token_use=access and client_id (not aud). Reject ID tokens and other clients. */
public class CognitoAccessTokenValidator implements OAuth2TokenValidator<Jwt> {

    private final String clientId;

    public CognitoAccessTokenValidator(String clientId) {
        this.clientId = clientId;
    }

    @Override
    public OAuth2TokenValidatorResult validate(Jwt jwt) {
        if (!"access".equals(jwt.getClaimAsString("token_use"))) {
            return fail("token_use must be access");
        }
        if (clientId == null || !clientId.equals(jwt.getClaimAsString("client_id"))) {
            return fail("token was issued to a different client");
        }
        return OAuth2TokenValidatorResult.success();
    }

    private static OAuth2TokenValidatorResult fail(String message) {
        return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", message, null));
    }
}
