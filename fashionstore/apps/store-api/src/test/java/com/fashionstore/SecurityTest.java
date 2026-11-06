package com.fashionstore;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fashionstore.auth.CognitoAccessTokenValidator;
import com.fashionstore.configuration.SecurityConfig;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;

class SecurityTest extends AbstractIntegrationTest {

    @Test
    void protectedEndpointsNeedAToken() throws Exception {
        mvc.perform(get("/api/cart")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/orders")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/checkouts").header("Idempotency-Key", java.util.UUID.randomUUID().toString()))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void scopesAreEnforced() throws Exception {
        var readOnly = jwt().jwt(j -> j.subject("u1"))
                .authorities(new SimpleGrantedAuthority(SecurityConfig.SCOPE_ORDERS));
        mvc.perform(get("/api/orders").with(readOnly)).andExpect(status().isOk());
        mvc.perform(get("/api/cart").with(readOnly)).andExpect(status().isForbidden());
    }

    @Test
    void unknownPathsAreDenied() throws Exception {
        mvc.perform(get("/api/admin").with(shopper("u1"))).andExpect(status().isForbidden());
        mvc.perform(get("/actuator/env")).andExpect(status().isUnauthorized());
    }

    @Test
    void validatorAcceptsOnlyAccessTokensForOurClient() {
        var v = new CognitoAccessTokenValidator("test-client");
        assertThat(v.validate(token("access", "test-client")).hasErrors()).isFalse();
        assertThat(v.validate(token("id", "test-client")).hasErrors()).isTrue();
        assertThat(v.validate(token("access", "other-client")).hasErrors()).isTrue();
    }

    private static Jwt token(String use, String clientId) {
        return Jwt.withTokenValue("t").header("alg", "RS256").subject("u")
                .claim("token_use", use).claim("client_id", clientId)
                .issuedAt(Instant.now()).expiresAt(Instant.now().plusSeconds(60)).build();
    }
}
