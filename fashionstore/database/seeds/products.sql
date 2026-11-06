-- Demo catalogue (synthetic). Re-runnable.
INSERT INTO products (sku, name, description, category, colour, size, price_cents, image_url) VALUES
  ('DRS-001-S', 'Linen Midi Dress',       'Breathable linen midi dress.',     'dresses',  'sand',  'S', 5990, '/images/drs-001.svg'),
  ('DRS-001-M', 'Linen Midi Dress',       'Breathable linen midi dress.',     'dresses',  'sand',  'M', 5990, '/images/drs-001.svg'),
  ('DRS-002-M', 'Satin Slip Dress',       'Bias-cut satin slip dress.',       'dresses',  'black', 'M', 7990, '/images/drs-002.svg'),
  ('TOP-001-S', 'Ribbed Knit Top',        'Fitted ribbed knit top.',          'tops',     'cream', 'S', 2990, '/images/top-001.svg'),
  ('TOP-002-M', 'Oversized Poplin Shirt', 'Crisp cotton poplin shirt.',       'tops',     'white', 'M', 3990, '/images/top-002.svg'),
  ('BTM-001-M', 'Wide-Leg Trousers',      'High-rise wide-leg trousers.',     'bottoms',  'navy',  'M', 4990, '/images/btm-001.svg'),
  ('BTM-002-S', 'Pleated Midi Skirt',     'Pleated satin midi skirt.',        'bottoms',  'olive', 'S', 4490, '/images/btm-002.svg'),
  ('BAG-001',   'Woven Tote Bag',         'Hand-woven raffia tote.',          'bags',     'natural', NULL, 6990, '/images/bag-001.svg'),
  ('SHO-001-38','Strappy Sandals',        'Leather strappy flat sandals.',    'shoes',    'tan',   '38', 5490, '/images/sho-001.svg'),
  ('FLASH-001', 'Flash Sale Blazer',      'Limited flash-sale blazer.',       'outerwear','black', 'M', 9990, '/images/flash-001.svg')
ON DUPLICATE KEY UPDATE name = VALUES(name), price_cents = VALUES(price_cents), active = TRUE;
