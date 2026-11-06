package com.fashionstore.checkout;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CheckoutStatus(
        @JsonProperty("checkout_id") String checkoutId,
        String status,
        String reason,
        @JsonProperty("order_id") Long orderId) {}
