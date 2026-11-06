-- Compare with Athena daily-revenue: distinct order_id count and summed revenue for the same day.
SELECT DATE(created_at) AS order_date,
       COUNT(*)         AS confirmed_orders,
       SUM(total_cents) AS revenue_cents
FROM orders
WHERE status = 'CONFIRMED'
GROUP BY DATE(created_at)
ORDER BY order_date DESC;
