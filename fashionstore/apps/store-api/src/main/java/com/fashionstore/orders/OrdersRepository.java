package com.fashionstore.orders;

import java.sql.Timestamp;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class OrdersRepository {

    private final JdbcClient jdbc;

    public OrdersRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Orders owned by {@code userSub}, newest first. */
    public List<Order> list(String userSub, int limit) {
        return jdbc.sql("""
                SELECT order_id, checkout_id, status, reason, total_cents, created_at FROM orders
                WHERE user_sub = :u ORDER BY created_at DESC, order_id DESC LIMIT :limit
                """).param("u", userSub).param("limit", limit)
                .query((rs, i) -> map(rs, List.of())).list();
    }

    public Optional<Order> find(String userSub, long orderId) {
        return jdbc.sql("""
                SELECT order_id, checkout_id, status, reason, total_cents, created_at FROM orders
                WHERE order_id = :id AND user_sub = :u
                """).param("id", orderId).param("u", userSub)
                .query((rs, i) -> map(rs, items(orderId))).optional();
    }

    private List<Order.Item> items(long orderId) {
        return jdbc.sql("""
                SELECT oi.sku, p.name, oi.qty, oi.unit_price_cents FROM order_items oi
                JOIN products p ON p.sku = oi.sku WHERE oi.order_id = :id ORDER BY oi.sku
                """).param("id", orderId).query(Order.Item.class).list();
    }

    private static Order map(java.sql.ResultSet rs, List<Order.Item> items) throws java.sql.SQLException {
        Timestamp created = rs.getTimestamp("created_at");
        return new Order(rs.getLong("order_id"), rs.getString("checkout_id"), rs.getString("status"),
                rs.getString("reason"), rs.getInt("total_cents"), created.toInstant(), items);
    }
}
