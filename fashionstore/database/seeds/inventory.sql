-- Demo stock. FLASH-001 is deliberately scarce for the oversell test.
INSERT INTO inventory (sku, qty) VALUES
  ('DRS-001-S', 100), ('DRS-001-M', 100), ('DRS-002-M', 60),
  ('TOP-001-S', 150), ('TOP-002-M', 120), ('BTM-001-M', 80),
  ('BTM-002-S', 70),  ('BAG-001', 40),    ('SHO-001-38', 90),
  ('FLASH-001', 50)
ON DUPLICATE KEY UPDATE qty = VALUES(qty);
