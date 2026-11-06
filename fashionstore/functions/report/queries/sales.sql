-- Confirmed sales for one UTC day, per order and SKU. Params: start (inclusive), end (exclusive).
SELECT DATE_FORMAT(o.created_at, '%%Y-%%m-%%d') AS order_date,
       oi.sku,
       p.category,
       o.order_id,
       SUM(oi.qty)                           AS units,
       SUM(oi.qty * oi.unit_price_cents)     AS revenue_cents
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p     ON p.sku = oi.sku
WHERE o.status = 'CONFIRMED'
  AND o.created_at >= %(start)s
  AND o.created_at <  %(end)s
GROUP BY order_date, oi.sku, p.category, o.order_id
ORDER BY revenue_cents DESC, oi.sku
