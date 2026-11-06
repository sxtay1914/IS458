import http from 'k6/http';
import { sleep } from 'k6';

export const BASE = (__ENV.BASE_URL || '').replace(/\/$/, '');
if (!BASE) throw new Error('BASE_URL is required, e.g. BASE_URL=https://dxxxx.cloudfront.net');

// open() is called from each entry script (tests/load/*.js) so relative paths
// mean the same thing whichever way k6 resolves them.
export const PROFILE_NAME = __ENV.PROFILE || 'smoke';

/** Access tokens, one per test shopper, from tests/load/make-tokens.sh. */
export function parseTokens(text) {
  const tokens = JSON.parse(text);
  if (!Array.isArray(tokens) || tokens.length === 0) throw new Error('tokens.json must be a non-empty array');
  return tokens;
}

/** Each VU owns one shopper, so two VUs never fight over the same cart. */
export function tokenForVu(tokens) {
  if (__VU > tokens.length) throw new Error(`VU ${__VU} has no shopper: create at least as many users as VUs`);
  return tokens[__VU - 1];
}

export function authed(token, extra = {}) {
  return { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...extra } };
}

export function uuidv4() {
  // RFC 4122 v4 from Math.random; good enough for idempotency keys in a load test.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** Polls a checkout with backoff like the storefront does; returns the final body or null. */
export function waitForOutcome(token, id, timeoutS = 120) {
  const start = Date.now();
  let delay = 0.5;
  while ((Date.now() - start) / 1000 < timeoutS) {
    const r = http.get(`${BASE}/api/checkouts/${id}`, { ...authed(token), tags: { name: 'GET /api/checkouts/{id}' } });
    if (r.status === 200 && r.json('status') !== 'PENDING') return r.json();
    sleep(delay);
    delay = Math.min(delay * 2, 4);
  }
  return null;
}
