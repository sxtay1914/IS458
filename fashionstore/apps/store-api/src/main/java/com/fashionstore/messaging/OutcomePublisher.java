package com.fashionstore.messaging;

/** Publishes a checkout-status event (contracts/events/checkout-status.schema.json). */
public interface OutcomePublisher {
    void publish(String checkoutId, String status, String eventJson);
}
