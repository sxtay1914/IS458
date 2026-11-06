package com.fashionstore.cart;

import com.fashionstore.auth.CurrentUser;
import com.fashionstore.catalog.CatalogRepository;
import com.fashionstore.common.ApiException;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/cart")
public class CartController {

    public record CartRequest(@NotNull @Size(max = 20) List<@Valid LineItem> items) {}

    public record Cart(List<LineItem> items, @JsonProperty("total_cents") int totalCents) {}

    private final CartRepository carts;
    private final CatalogRepository catalog;

    public CartController(CartRepository carts, CatalogRepository catalog) {
        this.carts = carts;
        this.catalog = catalog;
    }

    @GetMapping
    Cart get(@AuthenticationPrincipal Jwt jwt) {
        return view(carts.items(CurrentUser.from(jwt).sub()));
    }

    @PutMapping
    Cart put(@AuthenticationPrincipal Jwt jwt, @Valid @RequestBody CartRequest req) {
        Map<String, Integer> merged = new LinkedHashMap<>();
        for (LineItem i : req.items()) {
            merged.merge(i.sku(), i.qty(), Integer::sum);
        }
        if (merged.values().stream().anyMatch(q -> q > 20)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "QTY_LIMIT", "At most 20 of one item");
        }
        Map<String, Integer> prices = catalog.prices(merged.keySet());
        List<String> unknown = merged.keySet().stream().filter(s -> !prices.containsKey(s)).toList();
        if (!unknown.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "UNKNOWN_SKU", "Unknown items: " + unknown);
        }
        List<LineItem> items = merged.entrySet().stream().map(e -> new LineItem(e.getKey(), e.getValue())).toList();
        String sub = CurrentUser.from(jwt).sub();
        carts.replace(sub, items);
        return view(carts.items(sub));
    }

    private Cart view(List<LineItem> items) {
        Map<String, Integer> prices = catalog.prices(items.stream().map(LineItem::sku).toList());
        int total = items.stream().mapToInt(i -> prices.getOrDefault(i.sku(), 0) * i.qty()).sum();
        return new Cart(items, total);
    }
}
