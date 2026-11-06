package com.fashionstore;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.is;
import static org.mockito.Mockito.doReturn;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fashionstore.messaging.Reconciler;
import com.fashionstore.checkout.CheckoutRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import java.nio.file.Files;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

class CheckoutApiTest extends AbstractIntegrationTest {

    @Autowired ObjectMapper mapper;
    @Autowired Reconciler reconciler;
    @MockitoSpyBean CheckoutRepository checkouts;

    void fillCart(String user) throws Exception {
        mvc.perform(put("/api/cart").with(shopper(user)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"items\":[{\"sku\":\"FLASH-001\",\"qty\":1},{\"sku\":\"BAG-001\",\"qty\":2}]}"))
                .andExpect(status().isOk());
    }

    @Test
    void acceptsCheckoutStoresPendingAndEnqueuesSchemaValidMessage() throws Exception {
        fillCart("u1");
        String id = UUID.randomUUID().toString();

        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id))
                .andExpect(status().isAccepted())
                .andExpect(header().string("Location", "/api/checkouts/" + id))
                .andExpect(jsonPath("$.status", is("PENDING")));

        var row = db.queryForMap("SELECT status, enqueued_at, email FROM checkouts WHERE checkout_id = ?", id);
        assertThat(row.get("status")).isEqualTo("PENDING");
        assertThat(row.get("enqueued_at")).isNotNull();
        assertThat(row.get("email")).isEqualTo("u1@example.com");
        assertThat(db.queryForObject("SELECT COUNT(*) FROM cart_items WHERE user_sub = 'u1'", Integer.class)).isZero();

        assertThat(messaging.queued).hasSize(1);
        JsonNode msg = mapper.readTree(messaging.queued.get(0).json());
        assertThat(schema("checkout-request.schema.json").validate(msg)).isEmpty();
        assertThat(msg.get("items")).hasSize(2);
    }

    @Test
    void retryWithSameKeyIsIdempotent() throws Exception {
        fillCart("u1");
        String id = UUID.randomUUID().toString();
        for (int i = 0; i < 3; i++) {
            mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id))
                    .andExpect(status().isAccepted()).andExpect(jsonPath("$.checkout_id", is(id)));
        }
        assertThat(db.queryForObject("SELECT COUNT(*) FROM checkouts", Integer.class)).isEqualTo(1);
        assertThat(messaging.queued).hasSize(1);
    }

    @Test
    void concurrentRetriesCreateOneCheckout() throws Exception {
        fillCart("u1");
        String id = UUID.randomUUID().toString();
        Callable<Integer> call = () -> mvc.perform(post("/api/checkouts").with(shopper("u1"))
                .header("Idempotency-Key", id)).andReturn().getResponse().getStatus();
        try (var pool = Executors.newFixedThreadPool(6)) {
            var results = pool.invokeAll(IntStream.range(0, 6).mapToObj(i -> call).toList());
            for (var r : results) {
                assertThat(r.get()).isEqualTo(202);
            }
        }
        assertThat(db.queryForObject("SELECT COUNT(*) FROM checkouts", Integer.class)).isEqualTo(1);
        assertThat(messaging.queued).hasSize(1);
    }

    @Test
    void retryRecoversWhenAnotherRequestAlreadyConsumedTheCart() throws Exception {
        fillCart("u1");
        String id = UUID.randomUUID().toString();
        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id))
                .andExpect(status().isAccepted());

        // The retry's first lookup happened before the winning request committed.
        doReturn(Optional.empty()).doCallRealMethod().when(checkouts).find(id);
        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.checkout_id", is(id)));

        assertThat(db.queryForObject("SELECT COUNT(*) FROM checkouts", Integer.class)).isEqualTo(1);
        assertThat(messaging.queued).hasSize(1);
    }

    @Test
    void anotherShopperCannotReuseOrReadTheCheckout() throws Exception {
        fillCart("u1");
        fillCart("u2");
        String id = UUID.randomUUID().toString();
        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id))
                .andExpect(status().isAccepted());
        mvc.perform(post("/api/checkouts").with(shopper("u2")).header("Idempotency-Key", id))
                .andExpect(status().isConflict());
        mvc.perform(get("/api/checkouts/" + id).with(shopper("u2"))).andExpect(status().isNotFound());
        mvc.perform(get("/api/checkouts/" + id).with(shopper("u1"))).andExpect(status().isOk());
    }

    @Test
    void emptyCartAndBadKeysAreRejected() throws Exception {
        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", UUID.randomUUID().toString()))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.error", is("EMPTY_CART")));
        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", "not-a-uuid"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.error", is("INVALID_ID")));
        mvc.perform(post("/api/checkouts").with(shopper("u1")))
                .andExpect(status().isBadRequest());
    }

    @Test
    void statusReflectsTheOutcomeWrittenByTheLambda() throws Exception {
        fillCart("u1");
        String id = UUID.randomUUID().toString();
        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id));
        // what process-checkout does on success
        db.update("INSERT INTO orders (checkout_id, user_sub, email, status, total_cents) VALUES (?, 'u1', 'u1@example.com', 'CONFIRMED', 23970)", id);
        db.update("UPDATE checkouts SET status = 'CONFIRMED' WHERE checkout_id = ?", id);

        mvc.perform(get("/api/checkouts/" + id).with(shopper("u1")))
                .andExpect(jsonPath("$.status", is("CONFIRMED")))
                .andExpect(jsonPath("$.order_id").isNumber());
    }

    @Test
    void sqsOutageStillAcceptsAndReconcilerDispatchesLater() throws Exception {
        fillCart("u1");
        String id = UUID.randomUUID().toString();
        messaging.failNextSends.set(1);

        mvc.perform(post("/api/checkouts").with(shopper("u1")).header("Idempotency-Key", id))
                .andExpect(status().isAccepted());
        assertThat(messaging.queued).isEmpty();
        assertThat(db.queryForObject("SELECT enqueued_at FROM checkouts WHERE checkout_id = ?", Object.class, id)).isNull();

        assertThat(reconciler.dispatchPending()).isEqualTo(1);
        assertThat(messaging.queued).hasSize(1);
        assertThat(db.queryForObject("SELECT enqueued_at FROM checkouts WHERE checkout_id = ?", Object.class, id)).isNotNull();
        assertThat(db.queryForObject("SELECT COUNT(*) FROM reconciliation_log WHERE kind = 'DISPATCH'", Integer.class)).isEqualTo(1);
        assertThat(reconciler.dispatchPending()).isZero();
    }

    JsonSchema schema(String name) throws Exception {
        String text = Files.readString(REPO_ROOT.resolve("contracts/events").resolve(name));
        return JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(text);
    }
}
