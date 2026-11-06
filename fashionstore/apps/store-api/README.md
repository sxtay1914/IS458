# store-api (Spring Boot 3.5, Java 21)

The REST API behind `https://<cloudfront>/api/*`. Runs on EKS as two Deployments
(`store-api-v1` ×2, `store-api-v2` ×1) behind the internal ALB's weighted 90/10 rule.
Contract: [`contracts/openapi.yaml`](../../contracts/openapi.yaml).

| Package | What it does |
| --- | --- |
| `configuration` | Typed `fashionstore.*` settings, AWS clients, DB credentials from Secrets Manager, Spring Security (JWT resource server, scope rules) |
| `auth` | Accepts only Cognito **access** tokens for our client; finds the shopper's email (claim or `/oauth2/userInfo`) |
| `catalog` | `GET /products`, `GET /products/{sku}` with live stock (public) |
| `cart` | `GET/PUT /cart`, server-side, merged by SKU, max 20 per line |
| `checkout` | `POST /checkouts` (Idempotency-Key = checkout_id) and `GET /checkouts/{id}` (owner only) |
| `orders` | `GET /orders`, `GET /orders/{id}` (owner only; others get 404) |
| `messaging` | SQS sender, SNS publisher, in-memory fakes, and the **Reconciler** |
| `common` | Error format `{error, message, correlation_id}`, `X-Correlation-Id`, `/version` |

## How a checkout stays correct

1. One transaction: insert `checkouts` row (PENDING, request JSON) and clear the cart.
2. After commit: send to SQS, then mark `enqueued_at`. If SQS fails the shopper still gets 202.
3. The Reconciler (every 15 s, `FOR UPDATE SKIP LOCKED`, safe with 3 pods) re-sends PENDING rows
   never enqueued after 30 s, and re-publishes outcomes that process-checkout recorded but did not publish.
4. A retry with the same key returns the same checkout, including when another request consumed the cart after the first lookup. Another shopper's key gets 409.

## Run and test

```bash
make db-local-up db-migrate db-seed      # MySQL 8 on :3306
make api-run                             # :8080, messaging in memory, no AWS
make api-test                            # 24 tests, Testcontainers MySQL (needs Docker)
make push-api TAG=v1                     # build linux/amd64 image, push to ECR
```

Tests: `CatalogApiTest`, `SecurityTest` (no token, scope rules, unknown paths denied, ID tokens and other clients refused),
`CartApiTest`, `CheckoutApiTest` (idempotency, key reuse, empty cart, SQS outage → PENDING),
`OrdersAndReconcilerTest` (ownership, reconciler dispatch + republish, SKIP LOCKED).
