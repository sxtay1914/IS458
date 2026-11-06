-- Each must return zero rows.
SELECT checkout_id, COUNT(*) FROM orders GROUP BY checkout_id HAVING COUNT(*) > 1;
SELECT checkout_id, COUNT(*) FROM notification_log GROUP BY checkout_id HAVING COUNT(*) > 1;
-- Notifications that needed more than one attempt (possible logged duplicates).
SELECT checkout_id, attempts FROM notification_log WHERE attempts > 1;
