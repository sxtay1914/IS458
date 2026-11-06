package com.fashionstore.messaging;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * fashionstore.messaging=memory: keeps messages in memory instead of SQS/SNS.
 * Used for local runs without AWS and by the tests (which can also inject failures).
 */
@Component
@ConditionalOnProperty(name = "fashionstore.messaging", havingValue = "memory")
public class InMemoryMessaging implements CheckoutQueue, OutcomePublisher {

    private static final Logger log = LoggerFactory.getLogger(InMemoryMessaging.class);

    public record Sent(String checkoutId, String json) {}

    public final List<Sent> queued = new CopyOnWriteArrayList<>();
    public final List<Sent> published = new CopyOnWriteArrayList<>();
    public final AtomicInteger failNextSends = new AtomicInteger();
    public final AtomicInteger failNextPublishes = new AtomicInteger();

    @Override
    public void send(String checkoutId, String messageJson) {
        if (failNextSends.getAndUpdate(n -> Math.max(0, n - 1)) > 0) {
            throw new IllegalStateException("simulated SQS outage");
        }
        log.info("checkout queued (memory) {}", checkoutId);
        queued.add(new Sent(checkoutId, messageJson));
    }

    @Override
    public void publish(String checkoutId, String status, String eventJson) {
        if (failNextPublishes.getAndUpdate(n -> Math.max(0, n - 1)) > 0) {
            throw new IllegalStateException("simulated SNS outage");
        }
        log.info("outcome published (memory) {} {}", checkoutId, status);
        published.add(new Sent(checkoutId, eventJson));
    }

    public void reset() {
        queued.clear();
        published.clear();
        failNextSends.set(0);
        failNextPublishes.set(0);
    }
}
