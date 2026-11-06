-- Current stock snapshot for every product.
SELECT i.sku, p.name, p.category, i.qty,
       DATE_FORMAT(i.updated_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS updated_at
FROM inventory i
JOIN products p ON p.sku = i.sku
ORDER BY i.qty ASC, i.sku
