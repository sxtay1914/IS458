# Contracts

The seam between the platform half and the application half of the team.

| File | Producer | Consumer |
| --- | --- | --- |
| `openapi.yaml` | store-api | storefront |
| `events/checkout-request.schema.json` | store-api (SQS `checkout-requests`) | process-checkout λ |
| `events/checkout-status.schema.json` | process-checkout λ, store-api reconciler (SNS `checkout-status`) | notifier λ, store-api |

Rules: messages are at-least-once, so every consumer dedupes on `checkout_id`.
Prices are never taken from a message. A change to a schema needs a new
`schema_version`. The examples are validated in the functions test suite.
