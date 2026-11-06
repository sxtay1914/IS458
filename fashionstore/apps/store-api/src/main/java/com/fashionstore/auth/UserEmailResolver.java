package com.fashionstore.auth;

import com.fashionstore.common.ApiException;
import com.fashionstore.configuration.AppProperties;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * Cognito access tokens do not contain the email address. Read it from the
 * token if present, otherwise from the Cognito userInfo endpoint (needs the
 * openid scope), cached per subject.
 */
@Component
public class UserEmailResolver {

    private final RestClient http;
    private final String userInfoUrl;
    private final Map<String, String> cache = new ConcurrentHashMap<>();

    public UserEmailResolver(AppProperties props, RestClient.Builder builder) {
        this.http = builder.build();
        String domain = props.cognito().domain();
        this.userInfoUrl = domain == null || domain.isBlank() ? null : "https://" + domain + "/oauth2/userInfo";
    }

    public String emailOf(CurrentUser user) {
        String claim = user.jwt().getClaimAsString("email");
        if (claim != null && !claim.isBlank()) {
            return claim;
        }
        return cache.computeIfAbsent(user.sub(), sub -> fetch(user));
    }

    @SuppressWarnings("unchecked")
    private String fetch(CurrentUser user) {
        if (userInfoUrl == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "EMAIL_UNAVAILABLE", "No email on the token");
        }
        Map<String, Object> info = http.get().uri(userInfoUrl)
                .header("Authorization", "Bearer " + user.jwt().getTokenValue())
                .retrieve().body(Map.class);
        Object email = info == null ? null : info.get("email");
        if (email == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "EMAIL_UNAVAILABLE", "Cognito returned no email");
        }
        return email.toString();
    }
}
