-- One notification row per checkout. UNIQUE(checkout_id) plus a short lease
-- (claimed_until) stops two notifier invocations from emailing the same
-- shopper at the same time.
-- Known window: a crash after SES accepts the mail and before status=SENT
-- commits causes one duplicate on retry, visible as attempts > 1.
CREATE TABLE notification_log (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  checkout_id     CHAR(36)     NOT NULL,
  email           VARCHAR(254) NOT NULL,
  outcome         ENUM('CONFIRMED','REJECTED') NOT NULL,
  status          ENUM('SENDING','SENT','FAILED') NOT NULL DEFAULT 'SENDING',
  attempts        INT UNSIGNED NOT NULL DEFAULT 0,
  ses_message_id  VARCHAR(128) NULL,
  last_error      VARCHAR(500) NULL,
  claimed_until   TIMESTAMP(3) NULL,
  created_at      TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  sent_at         TIMESTAMP(3) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_notification_checkout_id (checkout_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Audit of reconciler actions (dispatch re-sends and outcome re-publishes),
-- used as evidence for the failure-recovery tests.
CREATE TABLE reconciliation_log (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  kind         ENUM('DISPATCH','OUTCOME') NOT NULL,
  checkout_id  CHAR(36)     NOT NULL,
  created_at   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_reconciliation_checkout (checkout_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
