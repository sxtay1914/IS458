package com.fashionstore.auth;

import com.fashionstore.common.ApiException;
import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jwt.Jwt;

/** The shopper behind the request. Ownership checks always use {@code sub}, never client input. */
public record CurrentUser(String sub, Jwt jwt) {

    public static CurrentUser from(Jwt jwt) {
        if (jwt == null || jwt.getSubject() == null) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "UNAUTHENTICATED", "Sign in first");
        }
        return new CurrentUser(jwt.getSubject(), jwt);
    }
}
