package com.fashionstore.messaging;

import com.fashionstore.configuration.AppProperties;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Timestamp;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Closes both commit/publish gaps:
 *   dispatch: checkouts PENDING with enqueued_at NULL (SQS send failed or pod died) -> re-send
 *   outcome:  orders with outcome_published_at NULL (Lambda died after commit)      -> re-publish
 * Every pod runs it; FOR UPDATE SKIP LOCKED makes pods take disjoint rows, so a
 * row is never handled by two pods at once. Consumers dedupe on checkout_id anyway.
 */
@Component
public class Reconciler {

    private static final Logger log = LoggerFactory.getLogger(Reconciler.class);

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;
    private final CheckoutQueue queue;
    private final OutcomePublisher publisher;
    private final ObjectMapper mapper;
    private final AppProperties.Reconciler cfg;

    public Reconciler(JdbcClient jdbc, TransactionTemplate tx, CheckoutQueue queue, OutcomePublisher publisher,
                      ObjectMapper mapper, AppProperties props) {
        this.jdbc = jdbc;
        this.tx = tx;
        this.queue = queue;
        this.publisher = publisher;
        this.mapper = mapper;
        this.cfg = props.reconciler();
    }

    @Scheduled(fixedDelayString = "${fashionstore.reconciler.interval-ms:15000}",
               initialDelayString = "${fashionstore.reconciler.initial-delay-ms:20000}")
    public void scheduled() {
        if (!cfg.enabled()) {
            return;
        }
        try {
            int d = dispatchPending();
            int o = republishOutcomes();
            if (d + o > 0) {
                log.info("reconciler re-sent {} checkouts and re-published {} outcomes", d, o);
            }
        } catch (RuntimeException e) {
            log.warn("reconciler pass failed: {}", e.toString());
        }
    }

    record Pending(String checkoutId, String requestJson) {}

    public int dispatchPending() {
        Integer n = tx.execute(status -> {
            List<Pending> rows = jdbc.sql("""
                    SELECT checkout_id, CAST(request_json AS CHAR) AS request_json FROM checkouts
                    WHERE status = 'PENDING' AND enqueued_at IS NULL
                      AND created_at < CURRENT_TIMESTAMP(3) - INTERVAL :age SECOND
                    ORDER BY created_at LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                    """).param("age", cfg.dispatchAfterSeconds()).param("limit", cfg.batchSize())
                    .query(Pending.class).list();
            int sent = 0;
            for (Pending p : rows) {
                try {
                    queue.send(p.checkoutId(), p.requestJson());
                } catch (RuntimeException e) {
                    log.warn("re-send failed for {}: {}", p.checkoutId(), e.toString());
                    break; // queue unavailable: stop, rows stay NULL for the next pass
                }
                jdbc.sql("UPDATE checkouts SET enqueued_at = CURRENT_TIMESTAMP(3) WHERE checkout_id = :id")
                        .param("id", p.checkoutId()).update();
                audit("DISPATCH", p.checkoutId());
                sent++;
            }
            return sent;
        });
        return n == null ? 0 : n;
    }

    record Unpublished(long orderId, String checkoutId, String status, String reason, String userSub,
                       String email, int totalCents, Timestamp createdAt) {}

    public int republishOutcomes() {
        Integer n = tx.execute(status -> {
            List<Unpublished> rows = jdbc.sql("""
                    SELECT order_id, checkout_id, status, reason, user_sub, email, total_cents, created_at
                    FROM orders
                    WHERE outcome_published_at IS NULL
                      AND created_at < CURRENT_TIMESTAMP(3) - INTERVAL :age SECOND
                    ORDER BY created_at LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                    """).param("age", cfg.outcomeAfterSeconds()).param("limit", cfg.batchSize())
                    .query(Unpublished.class).list();
            int published = 0;
            for (Unpublished u : rows) {
                try {
                    publisher.publish(u.checkoutId(), u.status(), event(u));
                } catch (RuntimeException e) {
                    log.warn("re-publish failed for {}: {}", u.checkoutId(), e.toString());
                    break;
                }
                jdbc.sql("UPDATE orders SET outcome_published_at = CURRENT_TIMESTAMP(3) WHERE order_id = :id")
                        .param("id", u.orderId()).update();
                audit("OUTCOME", u.checkoutId());
                published++;
            }
            return published;
        });
        return n == null ? 0 : n;
    }

    private void audit(String kind, String checkoutId) {
        jdbc.sql("INSERT INTO reconciliation_log (kind, checkout_id) VALUES (:k, :id)")
                .param("k", kind).param("id", checkoutId).update();
    }

    /** Same shape process-checkout publishes (contracts/events/checkout-status.schema.json). */
    String event(Unpublished u) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("schema_version", 1);
        m.put("checkout_id", u.checkoutId());
        m.put("status", u.status());
        m.put("reason", u.reason());
        m.put("order_id", u.orderId());
        m.put("user_sub", u.userSub());
        m.put("email", u.email());
        m.put("total_cents", u.totalCents());
        m.put("occurred_at", u.createdAt().toInstant().truncatedTo(ChronoUnit.MILLIS).toString());
        try {
            return mapper.writeValueAsString(m);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}
