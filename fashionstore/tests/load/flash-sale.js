// Flash sale: every buyer tries to buy one FLASH-001 at the same instant.
// Pass = confirmed orders never exceed the stock that was on sale, and every
// buyer gets an answer (CONFIRMED or OUT_OF_STOCK) without the API erroring.
// Reset stock first:  make db-seed-remote   (FLASH-001 back to 50)
//   tests/load/make-tokens.sh 60 > tests/load/tokens.json
//   k6 run -e BASE_URL=... -e PROFILE=demo tests/load/flash-sale.js
// Afterwards run database/queries/verify-*.sql via the seed Job to cross-check.
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { BASE, PROFILE_NAME, authed, parseTokens, tokenForVu, uuidv4, waitForOutcome } from './lib/common.js';

const PROFILE = JSON.parse(open(`./profiles/${PROFILE_NAME}.json`));

const tokens = parseTokens(open(__ENV.TOKENS_FILE || './tokens.json'));
const buyers = Math.min(PROFILE.flash_sale.buyers, tokens.length);
export const options = {
  scenarios: {
    flash: { executor: 'per-vu-iterations', vus: buyers, iterations: 1, maxDuration: '5m' },
  },
  thresholds: {
    'http_req_failed{name:POST /api/checkouts}': ['rate==0'],
    flash_unanswered: ['count==0'],
  },
};

const confirmed = new Counter('flash_confirmed');
const soldOut = new Counter('flash_sold_out');
const unanswered = new Counter('flash_unanswered');

export function setup() {
  const stock = http.get(`${BASE}/api/products/FLASH-001`).json('stock');
  console.log(`FLASH-001 stock before the sale: ${stock}, buyers: ${buyers}`);
  return { stock };
}

export default function () {
  const token = tokenForVu(tokens);
  http.put(`${BASE}/api/cart`, JSON.stringify({ items: [{ sku: 'FLASH-001', qty: 1 }] }), authed(token));
  const key = uuidv4();
  const r = http.post(`${BASE}/api/checkouts`, null,
    { ...authed(token, { 'Idempotency-Key': key }), tags: { name: 'POST /api/checkouts' } });
  check(r, { accepted: (x) => x.status === 202 });
  const o = r.status === 202 ? waitForOutcome(token, key, 240) : null;
  if (!o) return unanswered.add(1);
  if (o.status === 'CONFIRMED') confirmed.add(1);
  else if (o.reason === 'OUT_OF_STOCK') soldOut.add(1);
}

export function teardown(data) {
  const after = http.get(`${BASE}/api/products/FLASH-001`).json('stock');
  console.log(`FLASH-001 stock after: ${after} (was ${data.stock}). Never negative => no oversell.`);
  if (after < 0) throw new Error('OVERSOLD: stock went negative');
}

export function handleSummary(data) {
  const n = (m) => (data.metrics[m] ? data.metrics[m].values.count : 0);
  const line = `confirmed=${n('flash_confirmed')} sold_out=${n('flash_sold_out')} unanswered=${n('flash_unanswered')}`;
  return { stdout: `\nFlash sale: ${line}\n`, 'flash-sale-summary.json': JSON.stringify(data, null, 2) };
}
