package com.fashionstore;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fashionstore.messaging.Reconciler;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import java.nio.file.Files;
import java.sql.Connection;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class OrdersAndReconcilerTest extends AbstractIntegrationTest {

    @Autowired Reconciler reconciler;
    @Autowired ObjectMapper mapper;

    long order(String user, String status, String reason, boolean published) {
        String cid = UUID.randomUUID().toString();
        db.update("INSERT INTO orders (checkout_id, user_sub, email, status, reason, total_cents, outcome_published_at) "
                + "VALUES (?, ?, ?, ?, ?, 5990, " + (published ? "CURRENT_TIMESTAMP(3)" : "NULL") + ")",
                cid, user, user + "@example.com", status, reason);
        Long id = db.queryForObject("SELECT order_id FROM orders WHERE checkout_id = ?", Long.class, cid);
        db.update("INSERT INTO order_items (order_id, sku, qty, unit_price_cents) VALUES (?, 'DRS-001-M', 1, 5990)", id);
        return id;
    }

    @Test
    void shopperSeesOnlyOwnOrders() throws Exception {
        long mine = order("u1", "CONFIRMED", null, true);
        order("u1", "REJECTED", "OUT_OF_STOCK", true);
        long theirs = order("u2", "CONFIRMED", null, true);

        mvc.perform(get("/api/orders").with(shopper("u1"))).andExpect(jsonPath("$", hasSize(2)));
        mvc.perform(get("/api/orders/" + mine).with(shopper("u1")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].name", is("Linen Midi Dress")));
        mvc.perform(get("/api/orders/" + theirs).with(shopper("u1"))).andExpect(status().isNotFound());
    }

    @Test
    void republishesOutcomesTheLambdaNeverPublished() throws Exception {
        order("u1", "CONFIRMED", null, true);
        order("u1", "REJECTED", "PAYMENT_DECLINED", false);

        assertThat(reconciler.republishOutcomes()).isEqualTo(1);
        assertThat(messaging.published).hasSize(1);
        var event = mapper.readTree(messaging.published.get(0).json());
        var schema = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012)
                .getSchema(Files.readString(REPO_ROOT.resolve("contracts/events/checkout-status.schema.json")));
        assertThat(schema.validate(event)).isEmpty();
        assertThat(event.get("reason").asText()).isEqualTo("PAYMENT_DECLINED");
        assertThat(db.queryForObject("SELECT COUNT(*) FROM orders WHERE outcome_published_at IS NULL", Integer.class)).isZero();
        assertThat(reconciler.republishOutcomes()).isZero();
    }

    @Test
    void publishFailureLeavesRowForNextPass() {
        order("u1", "CONFIRMED", null, false);
        messaging.failNextPublishes.set(1);
        assertThat(reconciler.republishOutcomes()).isZero();
        assertThat(db.queryForObject("SELECT COUNT(*) FROM orders WHERE outcome_published_at IS NULL", Integer.class)).isEqualTo(1);
        assertThat(reconciler.republishOutcomes()).isEqualTo(1);
    }

    @Test
    void skipLockedLeavesRowsHeldByAnotherPod() throws Exception {
        long locked = order("u1", "CONFIRMED", null, false);
        order("u2", "CONFIRMED", null, false);

        try (Connection other = dataSource.getConnection()) {   // "another pod" mid-pass
            other.setAutoCommit(false);
            try (var st = other.prepareStatement("SELECT order_id FROM orders WHERE order_id = ? FOR UPDATE")) {
                st.setLong(1, locked);
                st.executeQuery();
            }
            assertThat(reconciler.republishOutcomes()).isEqualTo(1);   // skipped the locked row, no waiting
            other.rollback();
        }
        assertThat(reconciler.republishOutcomes()).isEqualTo(1);       // picked up on the next pass
        assertThat(messaging.published).hasSize(2);
    }
}
