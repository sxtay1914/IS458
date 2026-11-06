package com.fashionstore.cart;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record LineItem(@NotBlank @Size(max = 64) String sku, @Min(1) @Max(20) int qty) {}
