package com.fashionstore.messaging;

/** Sends a checkout-request message (contracts/events/checkout-request.schema.json). */
public interface CheckoutQueue {
    void send(String checkoutId, String messageJson);
}
