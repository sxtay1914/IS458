package com.fashionstore.checkout;

import com.fashionstore.cart.CartRepository;
import com.fashionstore.cart.LineItem;
import com.fashionstore.catalog.CatalogRepository;
import com.fashionstore.common.ApiException;
import com.fashionstore.common.CorrelationIdFilter;
import com.fashionstore.messaging.CheckoutQueue;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Accepts a checkout of the shopper's cart:
 *   1. one transaction: insert checkouts (PENDING, enqueued_at NULL) and clear the cart
 *   2. send to SQS, then set enqueued_at
 * If step 2 fails the shopper still gets 202; the reconciler re-sends rows that
 * stay PENDING with enqueued_at NULL. The Idempotency-Key is the checkout_id,
 * so a retried POST returns the same checkout instead of creating a second one.
 */
@Service
public class CheckoutService {

    private static final Logger log = LoggerFactory.getLogger(CheckoutService.class);

    private final CheckoutRepository checkouts;
    private final CartRepository carts;
    private final CatalogRepository catalog;
    private final CheckoutQueue queue;
    private final TransactionTemplate tx;
    private final ObjectMapper mapper;

    public CheckoutService(CheckoutRepository checkouts, CartRepository carts, CatalogRepository catalog,
                           CheckoutQueue queue, TransactionTemplate tx, ObjectMapper mapper) {
        this.checkouts = checkouts;
        this.carts = carts;
        this.catalog = catalog;
        this.queue = queue;
        this.tx = tx;
        this.mapper = mapper;
    }

    public CheckoutStatus accept(String userSub, String email, String checkoutId) {
        var existing = checkouts.find(checkoutId);
        if (existing.isPresent()) {
            return replay(existing.get(), userSub);
        }

        String message;
        try {
            message = tx.execute(status -> {
                List<LineItem> items = carts.items(userSub);
                if (items.isEmpty()) {
                    throw new ApiException(HttpStatus.BAD_REQUEST, "EMPTY_CART", "The cart is empty");
                }
                var prices = catalog.prices(items.stream().map(LineItem::sku).toList());
                var unknown = items.stream().map(LineItem::sku).filter(s -> !prices.containsKey(s)).toList();
                if (!unknown.isEmpty()) {
                    throw new ApiException(HttpStatus.BAD_REQUEST, "UNKNOWN_SKU", "No longer sold: " + unknown);
                }
                String json = requestJson(checkoutId, userSub, email, items);
                checkouts.insertPending(checkoutId, userSub, email, json);
                carts.clear(userSub);
                return json;
            });
        } catch (DuplicateKeyException | ApiException failure) {
            // Re-read outside the rolled-back transaction to see a concurrent winner.
            var accepted = checkouts.find(checkoutId);
            if (accepted.isPresent()) {
                return replay(accepted.get(), userSub);
            }
            throw failure;
        }

        try {
            queue.send(checkoutId, message);
            checkouts.markEnqueued(checkoutId);
        } catch (RuntimeException e) {
            log.warn("enqueue failed for {}; the reconciler will retry: {}", checkoutId, e.toString());
        }
        return new CheckoutStatus(checkoutId, "PENDING", null, null);
    }

    public CheckoutStatus status(String userSub, String checkoutId) {
        var row = checkouts.find(checkoutId)
                .filter(r -> r.userSub().equals(userSub))   // another shopper's checkout looks like 404
                .orElseThrow(() -> ApiException.notFound("Checkout"));
        return new CheckoutStatus(row.checkoutId(), row.status(), row.reason(), row.orderId());
    }

    private CheckoutStatus replay(CheckoutRepository.Row row, String userSub) {
        if (!row.userSub().equals(userSub)) {
            throw new ApiException(HttpStatus.CONFLICT, "IDEMPOTENCY_KEY_REUSED", "Use a new Idempotency-Key");
        }
        return new CheckoutStatus(row.checkoutId(), row.status(), row.reason(), row.orderId());
    }

    private String requestJson(String checkoutId, String userSub, String email, List<LineItem> items) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("schema_version", 1);
        m.put("checkout_id", checkoutId);
        m.put("user_sub", userSub);
        m.put("email", email);
        m.put("items", items.stream().map(i -> Map.of("sku", i.sku(), "qty", i.qty())).toList());
        m.put("requested_at", Instant.now().truncatedTo(ChronoUnit.MILLIS).toString());
        m.put("correlation_id", CorrelationIdFilter.current());
        try {
            return mapper.writeValueAsString(m);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }
}
