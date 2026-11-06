-- Must return zero rows: no negative stock, and sold + remaining = seeded.
SELECT i.sku, i.qty AS remaining, COALESCE(SUM(oi.qty), 0) AS sold
FROM inventory i
LEFT JOIN order_items oi ON oi.sku = i.sku
LEFT JOIN orders o ON o.order_id = oi.order_id AND o.status = 'CONFIRMED'
GROUP BY i.sku, i.qty
HAVING i.qty < 0;
