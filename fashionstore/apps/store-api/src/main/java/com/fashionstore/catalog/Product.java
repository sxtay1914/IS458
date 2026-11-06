package com.fashionstore.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;

public record Product(
        String sku,
        String name,
        String description,
        String category,
        String colour,
        String size,
        @JsonProperty("price_cents") int priceCents,
        @JsonProperty("image_url") String imageUrl,
        int stock) {}
