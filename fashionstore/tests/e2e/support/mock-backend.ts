import type { Page, Route } from '@playwright/test';

/**
 * In-browser fake of Cognito and store-api, faithful to contracts/openapi.yaml:
 * cart and checkout need a Bearer token, POST /checkouts needs an
 * Idempotency-Key, outcomes arrive asynchronously (first poll is PENDING),
 * and a retry with the same key returns the same checkout.
 */
export const COGNITO = 'cognito.mock.test';

interface Product {
  sku: string; name: string; description: string; category: string; colour: string;
  size: string | null; price_cents: number; image_url: string; stock: number;
}

const PRODUCTS: Product[] = [
  { sku: 'DRS-001-M', name: 'Linen Midi Dress', description: 'Breathable linen midi dress.', category: 'dresses', colour: 'sand', size: 'M', price_cents: 5990, image_url: '/images/drs-001.svg', stock: 25 },
  { sku: 'TOP-002-M', name: 'Oversized Poplin Shirt', description: 'Crisp cotton poplin shirt.', category: 'tops', colour: 'white', size: 'M', price_cents: 3990, image_url: '/images/top-002.svg', stock: 25 },
  { sku: 'BAG-001', name: 'Woven Tote Bag', description: 'Hand-woven raffia tote.', category: 'bags', colour: 'natural', size: null, price_cents: 6990, image_url: '/images/bag-001.svg', stock: 25 },
  { sku: 'FLASH-001', name: 'Flash Sale Blazer', description: 'Limited flash-sale blazer.', category: 'outerwear', colour: 'black', size: 'M', price_cents: 9990, image_url: '/images/flash-001.svg', stock: 50 },
];

function b64url(s: string) {
  return Buffer.from(s).toString('base64url');
}

export function fakeIdToken(email: string) {
  return `${b64url('{"alg":"none"}')}.${b64url(JSON.stringify({ sub: `sub-${email}`, email }))}.x`;
}

export interface MockState {
  checkoutRequests: { key: string | null; authorization: string | null }[];
  failNextCheckouts: number;
}

export async function installMockBackend(page: Page, email: string): Promise<MockState> {
  const state: MockState = { checkoutRequests: [], failNextCheckouts: 0 };
  const cart: { sku: string; qty: number }[] = [];
  const checkouts = new Map<string, { status: string; reason: string | null; order_id: number; polls: number; items: typeof cart; total: number }>();
  let nextOrder = 1001;

  const json = (route: Route, status: number, body: unknown, headers: Record<string, string> = {}) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body), headers });
  const totalOf = (items: typeof cart) =>
    items.reduce((t, i) => t + i.qty * PRODUCTS.find((p) => p.sku === i.sku)!.price_cents, 0);

  await page.route('**/config.json', (r) =>
    json(r, 200, { apiBase: '/api', cognitoDomain: COGNITO, clientId: 'mock-client',
                   scopes: 'openid email fashionstore-api/checkout.write fashionstore-api/orders.read' }));

  // Hosted UI: "sign in" immediately and bounce back with a code.
  await page.route(`https://${COGNITO}/oauth2/authorize**`, (r) => {
    const u = new URL(r.request().url());
    const back = new URL(u.searchParams.get('redirect_uri')!);
    back.searchParams.set('code', 'mock-code');
    back.searchParams.set('state', u.searchParams.get('state')!);
    return r.fulfill({ status: 302, headers: { location: back.toString() } });
  });
  await page.route(`https://${COGNITO}/oauth2/token`, (r) => {
    const body = new URLSearchParams(r.request().postData() ?? '');
    if (body.get('code') !== 'mock-code' || !body.get('code_verifier')) return json(r, 400, { error: 'invalid_grant' });
    return json(r, 200, { access_token: 'mock-access', id_token: fakeIdToken(email), expires_in: 3600, token_type: 'Bearer' },
                { 'access-control-allow-origin': '*' });
  });
  await page.route(`https://${COGNITO}/logout**`, (r) =>
    r.fulfill({ status: 302, headers: { location: new URL(r.request().url()).searchParams.get('logout_uri')! } }));

  await page.route('**/api/**', async (r) => {
    const req = r.request();
    const url = new URL(req.url());
    const path = url.pathname.replace(/^\/api/, '');
    const authed = req.headers()['authorization'] === 'Bearer mock-access';

    if (req.method() === 'GET' && path === '/products') {
      const cat = url.searchParams.get('category');
      const inStock = url.searchParams.get('in_stock') === 'true';
      return json(r, 200, PRODUCTS.filter((p) => (!cat || p.category === cat) && (!inStock || p.stock > 0)));
    }
    if (req.method() === 'GET' && path.startsWith('/products/')) {
      const p = PRODUCTS.find((x) => x.sku === decodeURIComponent(path.slice(10)));
      return p ? json(r, 200, p) : json(r, 404, { error: 'NOT_FOUND' });
    }
    if (path === '/version') return json(r, 200, { version: 'v1' });
    if (!authed) return json(r, 401, { error: 'UNAUTHORIZED' });

    if (path === '/cart') {
      if (req.method() === 'PUT') {
        cart.splice(0, cart.length, ...(req.postDataJSON() as { items: typeof cart }).items);
      }
      return json(r, 200, { items: cart, total_cents: totalOf(cart) });
    }
    if (req.method() === 'POST' && path === '/checkouts') {
      const key = req.headers()['idempotency-key'] ?? null;
      state.checkoutRequests.push({ key, authorization: req.headers()['authorization'] ?? null });
      if (state.failNextCheckouts > 0) {
        state.failNextCheckouts--;
        return json(r, 503, { error: 'UNAVAILABLE', message: 'Service busy, please retry' });
      }
      if (!key) return json(r, 400, { error: 'MISSING_IDEMPOTENCY_KEY' });
      if (!checkouts.has(key)) {
        if (cart.length === 0) return json(r, 400, { error: 'EMPTY_CART', message: 'The cart is empty' });
        const declined = email.includes('+decline');
        const items = cart.splice(0, cart.length);
        checkouts.set(key, { status: declined ? 'REJECTED' : 'CONFIRMED', reason: declined ? 'PAYMENT_DECLINED' : null,
                             order_id: nextOrder++, polls: 0, items, total: totalOf(items) });
      }
      return json(r, 202, { checkout_id: key, status: 'PENDING', reason: null, order_id: null },
                  { location: `/api/checkouts/${key}` });
    }
    if (req.method() === 'GET' && path.startsWith('/checkouts/')) {
      const c = checkouts.get(path.slice(11));
      if (!c) return json(r, 404, { error: 'NOT_FOUND' });
      const done = ++c.polls > 1;
      return json(r, 200, done
        ? { checkout_id: path.slice(11), status: c.status, reason: c.reason, order_id: c.order_id }
        : { checkout_id: path.slice(11), status: 'PENDING', reason: null, order_id: null });
    }
    const orders = [...checkouts.entries()].filter(([, c]) => c.polls > 1).map(([id, c]) => ({
      order_id: c.order_id, checkout_id: id, status: c.status, reason: c.reason, total_cents: c.total,
      created_at: new Date().toISOString(),
      items: c.items.map((i) => {
        const p = PRODUCTS.find((x) => x.sku === i.sku)!;
        return { sku: i.sku, qty: i.qty, name: p.name, unit_price_cents: p.price_cents };
      }),
    })).reverse();
    if (path === '/orders') return json(r, 200, orders);
    if (path.startsWith('/orders/')) {
      const o = orders.find((x) => String(x.order_id) === path.slice(8));
      return o ? json(r, 200, o) : json(r, 404, { error: 'NOT_FOUND' });
    }
    return json(r, 404, { error: 'NOT_FOUND' });
  });
  return state;
}
