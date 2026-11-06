package com.fashionstore.configuration;

import com.fashionstore.auth.CognitoAccessTokenValidator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Cognito access tokens (Authorization: Bearer). Catalogue, version and health
 * are public; cart and checkout need the checkout.write scope; orders need orders.read.
 */
@Configuration
public class SecurityConfig {

    public static final String SCOPE_CHECKOUT = "SCOPE_fashionstore-api/checkout.write";
    public static final String SCOPE_ORDERS = "SCOPE_fashionstore-api/orders.read";

    @Bean
    SecurityFilterChain api(HttpSecurity http) throws Exception {
        http.csrf(c -> c.disable())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(a -> a
                        .requestMatchers(HttpMethod.GET, "/api/products", "/api/products/**").permitAll()
                        .requestMatchers("/api/version", "/actuator/health/**", "/actuator/info").permitAll()
                        .requestMatchers("/api/cart", "/api/cart/**").hasAuthority(SCOPE_CHECKOUT)
                        .requestMatchers("/api/checkouts", "/api/checkouts/**").hasAuthority(SCOPE_CHECKOUT)
                        .requestMatchers("/api/orders", "/api/orders/**").hasAuthority(SCOPE_ORDERS)
                        .anyRequest().denyAll())
                .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()));
        return http.build();
    }

    @Bean
    JwtDecoder jwtDecoder(AppProperties props) {
        String issuer = props.cognito().issuerUrl();
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(issuer + "/.well-known/jwks.json").build();
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(issuer),
                new CognitoAccessTokenValidator(props.cognito().clientId())));
        return decoder;
    }
}
