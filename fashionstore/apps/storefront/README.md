# storefront (React 19 + Vite)

Single-page app served from the private S3 bucket through CloudFront. Talks to
`/api/*` on the same origin, so no CORS. Sign-in is Cognito hosted UI with the
authorization code flow + PKCE (public client, no secret in the browser).

| Path | What it is |
| --- | --- |
| `public/config.json` | Runtime settings (API base, Cognito domain, client id, scopes). `scripts/deploy-storefront.sh` overwrites it from Terraform outputs, so one build works anywhere |
| `src/auth/pkce.ts` | PKCE verifier/challenge (RFC 7636), authorize URL, code exchange with state check |
| `src/auth/AuthContext.tsx` | Tokens in `sessionStorage` (gone when the tab closes) |
| `src/api/` | Typed client for every endpoint in `contracts/openapi.yaml` |
| `src/hooks/useCheckoutPolling.ts` | Polls a checkout with backoff 0.5 s → 4 s, gives up after 120 s |
| `src/pages/CheckoutPage.tsx` | Keeps one Idempotency-Key per attempt; a saved attempt can be retried after refresh even if the server cart is empty |
| `src/pages`, `src/components` | Products, details, bag, checkout, status, orders, auth callback |

```bash
npm ci
npm run dev        # :5173, proxies /api to store-api on :8080 (make api-run)
npm test           # 17 vitest tests (PKCE vector, API client, polling, checkout retry/refresh recovery, components)
npm run build      # dist/
```

For local sign-in set `cognitoDomain` and `clientId` in `public/config.json` and add
`http://localhost:5173/auth/callback` to the Cognito client's callback URLs.
