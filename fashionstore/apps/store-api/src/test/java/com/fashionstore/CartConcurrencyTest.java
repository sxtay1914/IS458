package com.fashionstore;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.spy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

import com.fashionstore.cart.CartRepository;
import com.fashionstore.cart.LineItem;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

class CartConcurrencyTest extends AbstractIntegrationTest {

    @Autowired CartRepository carts;
    @Autowired ObjectMapper mapper;
    @MockitoSpyBean JdbcClient jdbc;

    @Test
    void differentShoppersCanFillEmptyCartsConcurrently() throws Exception {
        var deleted = new CyclicBarrier(2);
        var deletes = new AtomicInteger();
        doAnswer(invocation -> {
            var statement = spy((JdbcClient.StatementSpec) invocation.callRealMethod());
            doAnswer(update -> {
                int changed = (Integer) update.callRealMethod();
                // Force both empty-cart deletes to finish before either inserts.
                if (deletes.incrementAndGet() <= 2) {
                    deleted.await(10, TimeUnit.SECONDS);
                }
                return changed;
            }).when(statement).update();
            return statement;
        }).when(jdbc).sql("DELETE FROM cart_items WHERE user_sub = :u");

        var first = List.of(new LineItem("BAG-001", 1));
        var second = List.of(new LineItem("BAG-001", 2));
        try (var pool = Executors.newFixedThreadPool(2)) {
            var a = pool.submit(() -> replace("cart-race-a", first));
            var b = pool.submit(() -> replace("cart-race-b", second));
            assertThat(a.get(20, TimeUnit.SECONDS)).isEqualTo(200);
            assertThat(b.get(20, TimeUnit.SECONDS)).isEqualTo(200);
        }
        assertThat(deletes.get()).isGreaterThanOrEqualTo(2);
        assertThat(carts.items("cart-race-a")).containsExactlyElementsOf(first);
        assertThat(carts.items("cart-race-b")).containsExactlyElementsOf(second);
    }

    @Test
    void failedReplacementPreservesThePreviousCart() {
        var original = List.of(new LineItem("BAG-001", 1));
        carts.replace("rollback-user", original);

        assertThatThrownBy(() -> carts.replace("rollback-user", List.of(
                new LineItem("FLASH-001", 2), new LineItem("NO-SUCH-SKU", 1))))
                .isInstanceOf(DataIntegrityViolationException.class);

        assertThat(carts.items("rollback-user")).containsExactlyElementsOf(original);
    }

    @Test
    void sameShopperReplacementsDoNotMixTheirItems() throws Exception {
        var start = new CyclicBarrier(2);
        var first = List.of(new LineItem("BAG-001", 1), new LineItem("FLASH-001", 2));
        var second = List.of(new LineItem("BAG-001", 3), new LineItem("FLASH-001", 4));
        try (var pool = Executors.newFixedThreadPool(2)) {
            var a = pool.submit(() -> {
                start.await(10, TimeUnit.SECONDS);
                return replace("same-shopper", first);
            });
            var b = pool.submit(() -> {
                start.await(10, TimeUnit.SECONDS);
                return replace("same-shopper", second);
            });
            assertThat(a.get(20, TimeUnit.SECONDS)).isEqualTo(200);
            assertThat(b.get(20, TimeUnit.SECONDS)).isEqualTo(200);
        }
        assertThat(carts.items("same-shopper")).isIn(first, second);
    }

    private int replace(String user, List<LineItem> items) throws Exception {
        return mvc.perform(put("/api/cart").with(shopper(user))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(Map.of("items", items))))
                .andReturn().getResponse().getStatus();
    }
}
