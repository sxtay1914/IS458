package com.fashionstore.checkout;

import com.fashionstore.auth.CurrentUser;
import com.fashionstore.auth.UserEmailResolver;
import com.fashionstore.common.ApiException;
import java.net.URI;
import java.util.Locale;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/checkouts")
public class CheckoutController {

    private final CheckoutService service;
    private final UserEmailResolver emails;

    public CheckoutController(CheckoutService service, UserEmailResolver emails) {
        this.service = service;
        this.emails = emails;
    }

    @PostMapping
    ResponseEntity<CheckoutStatus> accept(@AuthenticationPrincipal Jwt jwt,
                                          @RequestHeader("Idempotency-Key") String key) {
        String checkoutId = normaliseUuid(key);
        CurrentUser user = CurrentUser.from(jwt);
        CheckoutStatus status = service.accept(user.sub(), emails.emailOf(user), checkoutId);
        return ResponseEntity.accepted()
                .location(URI.create("/api/checkouts/" + checkoutId))
                .body(status);
    }

    @GetMapping("/{checkoutId}")
    CheckoutStatus status(@AuthenticationPrincipal Jwt jwt, @PathVariable String checkoutId) {
        return service.status(CurrentUser.from(jwt).sub(), normaliseUuid(checkoutId));
    }

    static String normaliseUuid(String value) {
        try {
            return UUID.fromString(value).toString().toLowerCase(Locale.ROOT);
        } catch (IllegalArgumentException e) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "INVALID_ID", "Expected a UUID");
        }
    }
}
