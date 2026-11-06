// Signed-in shoppers filling a cart and checking out, measuring time to outcome.
//   tests/load/make-tokens.sh 15 > tests/load/tokens.json
//   k6 run -e BASE_URL=... -e PROFILE=demo tests/load/checkout.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { BASE, PROFILE_NAME, authed, parseTokens, tokenForVu, uuidv4, waitForOutcome } from './lib/common.js';

const PROFILE = JSON.parse(open(`./profiles/${PROFILE_NAME}.json`));

const tokens = parseTokens(open(__ENV.TOKENS_FILE || './tokens.json'));
const p = PROFILE.checkout;
export const options = {
  scenarios: {
    checkout: p.stages
      ? { executor: 'ramping-vus', startVUs: 0, stages: p.stages }
      : { executor: 'constant-vus', vus: p.vus, duration: p.duration },
  },
  thresholds: {
    'http_req_duration{name:POST /api/checkouts}': ['p(95)<1000'],   // accept is fast: DB insert + SQS send
    checkout_to_outcome_ms: ['p(95)<30000'],                          // async processing under load
    checkout_timeouts: ['count==0'],
    checks: ['rate>0.99'],
  },
};

const outcomeMs = new Trend('checkout_to_outcome_ms', true);
const outcomes = new Counter('checkout_outcomes');
const timeouts = new Counter('checkout_timeouts');
// Everyday items with plenty of stock; FLASH-001 is left for flash-sale.js.
const SKUS = ['DRS-001-S', 'DRS-001-M', 'TOP-001-S', 'TOP-002-M', 'BTM-001-M', 'BAG-001', 'SHO-001-38'];

export default function () {
  const token = tokenForVu(tokens);
  const items = [{ sku: SKUS[Math.floor(Math.random() * SKUS.length)], qty: 1 }];
  const put = http.put(`${BASE}/api/cart`, JSON.stringify({ items }), { ...authed(token), tags: { name: 'PUT /api/cart' } });
  check(put, { 'cart saved': (r) => r.status === 200 });

  const key = uuidv4();
  const start = Date.now();
  const res = http.post(`${BASE}/api/checkouts`, null,
    { ...authed(token, { 'Idempotency-Key': key }), tags: { name: 'POST /api/checkouts' } });
  check(res, { 'checkout accepted (202)': (r) => r.status === 202 });
  if (res.status !== 202) return;

  const outcome = waitForOutcome(token, key);
  if (!outcome) {
    timeouts.add(1);
    return;
  }
  outcomeMs.add(Date.now() - start);
  outcomes.add(1, { status: outcome.status, reason: outcome.reason || 'none' });
  check(outcome, { 'not an unexpected rejection': (o) => o.status === 'CONFIRMED' || o.reason === 'OUT_OF_STOCK' });
  sleep(2 + Math.random() * 3);
}
