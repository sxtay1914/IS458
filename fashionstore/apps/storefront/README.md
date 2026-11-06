# storefront (React 19 + Vite)

Single-page app served from the private S3 bucket through CloudFront. Talks to
`/api/*` on the same origin, so no CORS. Sign-in is Cognito hosted UI with the
authorization code flow + PKCE (public client, no secret in the browser).

| Path | What it is |
| --- | --- |
| `public/config.json` | Runtime settings (API base, Cognito domain, client id, scopes). `scripts/deploy-storefront.sh` overwrites it from Terraform outputs, so one build works anywhere |
| `src/auth/pkce.ts` | PKCE verifier/challenge (RFC 7636), authorize URL, code exchange with state check |
| `src/auth/AuthContext.tsx` | Tokens in `sessionStorage` (gone when the tab closes) |
| `src/api/` | Typed client for every endpoint in `contracts/openapi.yaml`; `tests/contract.test.ts` fails if an endpoint, method, auth rule or query parameter drifts from the contract |
| `src/hooks/useCheckoutPolling.ts` | Polls a checkout with backoff 0.5 s → 4 s, gives up after 120 s |
| `src/pages/CheckoutPage.tsx` | Keeps one Idempotency-Key per attempt, so a retry never double-orders |
| `src/pages`, `src/components` | Products (category + in-stock filters), details, bag, checkout, status, orders, auth callback; footer shows the pilot version from `GET /api/version` |
| `src/styles/app.css` | Design tokens (palette, radii, 3D button edge) and all component styles; light and dark |

```bash
npm ci
npm run dev        # :5173, proxies /api to store-api on :8080 (make api-run)
npm test           # 21 vitest tests (PKCE vector, API client, contract coverage, polling, checkout retry, components)
npm run build      # dist/
```

## Look and feel

Playful and flat: rounded cards with 2px outlines, chunky buttons with a solid bottom edge that
presses down on click, pill category chips, a three-step checkout tracker (Bag → Review → Done),
animated pending / confirmed / rejected states, skeleton loading and friendly empty states.
Type is Nunito (SIL Open Font License, self-hosted from `@fontsource-variable/nunito`, no
third-party font requests). The palette is FashionStore's own (rose, violet, sun, mint), defined
once as CSS custom properties at the top of `src/styles/app.css`. Motion respects
`prefers-reduced-motion`.

For local sign-in set `cognitoDomain` and `clientId` in `public/config.json` and add
`http://localhost:5173/auth/callback` to the Cognito client's callback URLs.
