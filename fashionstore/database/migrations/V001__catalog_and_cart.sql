-- Catalog, stock and shopper carts.
CREATE TABLE products (
  sku          VARCHAR(64)  NOT NULL,
  name         VARCHAR(200) NOT NULL,
  description  TEXT         NULL,
  category     VARCHAR(64)  NOT NULL,
  colour       VARCHAR(32)  NULL,
  size         VARCHAR(16)  NULL,
  price_cents  INT UNSIGNED NOT NULL,
  image_url    VARCHAR(500) NULL,
  active       BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (sku),
  KEY idx_products_category (category, active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- qty can never go negative: the CHECK is a backstop for the conditional
-- decrement (UPDATE ... WHERE qty >= ?) used by process-checkout.
CREATE TABLE inventory (
  sku         VARCHAR(64)  NOT NULL,
  qty         INT          NOT NULL,
  updated_at  TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (sku),
  CONSTRAINT fk_inventory_product FOREIGN KEY (sku) REFERENCES products (sku),
  CONSTRAINT chk_inventory_qty_non_negative CHECK (qty >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE carts (
  user_sub    VARCHAR(64)  NOT NULL,
  updated_at  TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (user_sub)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE cart_items (
  user_sub  VARCHAR(64) NOT NULL,
  sku       VARCHAR(64) NOT NULL,
  qty       INT UNSIGNED NOT NULL,
  PRIMARY KEY (user_sub, sku),
  CONSTRAINT fk_cart_items_cart FOREIGN KEY (user_sub) REFERENCES carts (user_sub) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_product FOREIGN KEY (sku) REFERENCES products (sku),
  CONSTRAINT chk_cart_items_qty CHECK (qty BETWEEN 1 AND 20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
