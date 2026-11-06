-- Checkout requests accepted by store-api, and the single outcome per checkout.
--
-- checkouts: written by store-api in the same transaction that accepts the
--   request (202). enqueued_at stays NULL until SQS SendMessage succeeds; the
--   reconciler re-sends rows that stay PENDING with enqueued_at NULL.
CREATE TABLE checkouts (
  checkout_id   CHAR(36)     NOT NULL,
  user_sub      VARCHAR(64)  NOT NULL,
  email         VARCHAR(254) NOT NULL,
  status        ENUM('PENDING','CONFIRMED','REJECTED') NOT NULL DEFAULT 'PENDING',
  reason        VARCHAR(64)  NULL,
  request_json  JSON         NOT NULL,
  created_at    TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  enqueued_at   TIMESTAMP(3) NULL,
  updated_at    TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (checkout_id),
  KEY idx_checkouts_user (user_sub, created_at),
  KEY idx_checkouts_dispatch (status, enqueued_at, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- orders: exactly one row per checkout, CONFIRMED or REJECTED. The UNIQUE key
-- makes "one order per checkout" a database guarantee, not a code convention.
-- outcome_published_at stays NULL until the SNS publish succeeds; the
-- reconciler republishes rows where it is NULL.
CREATE TABLE orders (
  order_id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  checkout_id           CHAR(36)     NOT NULL,
  user_sub              VARCHAR(64)  NOT NULL,
  email                 VARCHAR(254) NOT NULL,
  status                ENUM('CONFIRMED','REJECTED') NOT NULL,
  reason                VARCHAR(64)  NULL,
  total_cents           INT UNSIGNED NOT NULL,
  payment_ref           VARCHAR(64)  NULL,
  created_at            TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  outcome_published_at  TIMESTAMP(3) NULL,
  PRIMARY KEY (order_id),
  UNIQUE KEY uq_orders_checkout_id (checkout_id),
  KEY idx_orders_user (user_sub, created_at),
  KEY idx_orders_unpublished (outcome_published_at, created_at),
  KEY idx_orders_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE order_items (
  order_id          BIGINT UNSIGNED NOT NULL,
  sku               VARCHAR(64)  NOT NULL,
  qty               INT UNSIGNED NOT NULL,
  unit_price_cents  INT UNSIGNED NOT NULL,
  PRIMARY KEY (order_id, sku),
  CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
  CONSTRAINT fk_order_items_product FOREIGN KEY (sku) REFERENCES products (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
