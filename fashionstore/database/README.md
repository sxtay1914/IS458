# Database

Flyway owns the schema. Migrations in `migrations/` are applied in order by the
`database-migration` Kubernetes Job (or locally with Docker, see below).

Correctness rules that live in the schema:

* `orders.checkout_id` and `notification_log.checkout_id` are UNIQUE.
* `inventory.qty` has `CHECK (qty >= 0)` behind the conditional decrement.
* `checkouts.enqueued_at` and `orders.outcome_published_at` are the markers the
  reconciler sweeps (dispatch side and outcome side).

Local run:

```bash
docker run -d --name fsdb -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=fashionstore -p 3306:3306 mysql:8.4
make db-migrate db-seed
```
