package com.fashionstore.orders;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

public record Order(
        @JsonProperty("order_id") long orderId,
        @JsonProperty("checkout_id") String checkoutId,
        String status,
        String reason,
        @JsonProperty("total_cents") int totalCents,
        @JsonProperty("created_at") Instant createdAt,
        List<Item> items) {

    public record Item(String sku, String name, int qty, @JsonProperty("unit_price_cents") int unitPriceCents) {}
}
