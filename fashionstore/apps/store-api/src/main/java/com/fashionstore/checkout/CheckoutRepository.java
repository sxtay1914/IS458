package com.fashionstore.checkout;

import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class CheckoutRepository {

    public record Row(String checkoutId, String userSub, String status, String reason, Long orderId) {}

    private final JdbcClient jdbc;

    public CheckoutRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Row> find(String checkoutId) {
        return jdbc.sql("""
                SELECT c.checkout_id, c.user_sub, c.status, c.reason, o.order_id
                FROM checkouts c LEFT JOIN orders o ON o.checkout_id = c.checkout_id
                WHERE c.checkout_id = :id
                """).param("id", checkoutId).query(Row.class).optional();
    }

    public void insertPending(String checkoutId, String userSub, String email, String requestJson) {
        jdbc.sql("""
                INSERT INTO checkouts (checkout_id, user_sub, email, status, request_json)
                VALUES (:id, :u, :e, 'PENDING', :json)
                """).param("id", checkoutId).param("u", userSub).param("e", email).param("json", requestJson).update();
    }

    public void markEnqueued(String checkoutId) {
        jdbc.sql("UPDATE checkouts SET enqueued_at = CURRENT_TIMESTAMP(3) WHERE checkout_id = :id AND enqueued_at IS NULL")
                .param("id", checkoutId).update();
    }
}
