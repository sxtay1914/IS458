package com.fashionstore.catalog;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class CatalogRepository {

    private static final String SELECT = """
            SELECT p.sku, p.name, p.description, p.category, p.colour, p.size, p.price_cents, p.image_url,
                   COALESCE(i.qty, 0) AS stock
            FROM products p LEFT JOIN inventory i ON i.sku = p.sku
            WHERE p.active = TRUE
            """;

    private final JdbcClient jdbc;

    public CatalogRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<Product> list(String category, Boolean inStock) {
        StringBuilder sql = new StringBuilder(SELECT);
        var params = new java.util.HashMap<String, Object>();
        if (category != null && !category.isBlank()) {
            sql.append(" AND p.category = :category");
            params.put("category", category);
        }
        if (Boolean.TRUE.equals(inStock)) {
            sql.append(" AND COALESCE(i.qty, 0) > 0");
        }
        sql.append(" ORDER BY p.category, p.name, p.sku");
        return jdbc.sql(sql.toString()).params(params).query(Product.class).list();
    }

    public Optional<Product> find(String sku) {
        return jdbc.sql(SELECT + " AND p.sku = :sku").param("sku", sku).query(Product.class).optional();
    }

    /** Price in cents for each active SKU among {@code skus}. */
    public Map<String, Integer> prices(Collection<String> skus) {
        if (skus.isEmpty()) {
            return Map.of();
        }
        return jdbc.sql("SELECT sku, price_cents FROM products WHERE active = TRUE AND sku IN (:skus)")
                .param("skus", skus)
                .query((rs, i) -> Map.entry(rs.getString(1), rs.getInt(2)))
                .list().stream().collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }
}
