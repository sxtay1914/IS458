package com.fashionstore.orders;

import com.fashionstore.auth.CurrentUser;
import com.fashionstore.common.ApiException;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Shopper order history. Another shopper's order is indistinguishable from a missing one (404). */
@RestController
@RequestMapping("/api/orders")
public class OrdersController {

    private final OrdersRepository repo;

    public OrdersController(OrdersRepository repo) {
        this.repo = repo;
    }

    @GetMapping
    List<Order> list(@AuthenticationPrincipal Jwt jwt) {
        return repo.list(CurrentUser.from(jwt).sub(), 50);
    }

    @GetMapping("/{orderId}")
    Order get(@AuthenticationPrincipal Jwt jwt, @PathVariable long orderId) {
        return repo.find(CurrentUser.from(jwt).sub(), orderId).orElseThrow(() -> ApiException.notFound("Order"));
    }
}
