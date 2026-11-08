package com.fashionstore.cart;

import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class CartRepository {

    private final JdbcClient jdbc;

    public CartRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<LineItem> items(String userSub) {
        return jdbc.sql("SELECT sku, qty FROM cart_items WHERE user_sub = :u ORDER BY sku")
                .param("u", userSub).query(LineItem.class).list();
    }

    // Empty-cart range deletes must not gap-lock another shopper's inserts.
    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void replace(String userSub, List<LineItem> items) {
        jdbc.sql("INSERT INTO carts (user_sub) VALUES (:u) ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP(3)")
                .param("u", userSub).update();
        jdbc.sql("DELETE FROM cart_items WHERE user_sub = :u").param("u", userSub).update();
        for (LineItem item : items) {
            jdbc.sql("INSERT INTO cart_items (user_sub, sku, qty) VALUES (:u, :sku, :qty)")
                    .param("u", userSub).param("sku", item.sku()).param("qty", item.qty()).update();
        }
    }

    public void clear(String userSub) {
        jdbc.sql("DELETE FROM cart_items WHERE user_sub = :u").param("u", userSub).update();
    }
}
