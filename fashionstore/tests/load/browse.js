// Anonymous browsing through CloudFront: catalogue, details, static assets.
//   k6 run -e BASE_URL=https://dxxxx.cloudfront.net -e PROFILE=demo tests/load/browse.js
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { BASE, PROFILE_NAME } from './lib/common.js';

const PROFILE = JSON.parse(open(`./profiles/${PROFILE_NAME}.json`));

const p = PROFILE.browse;
export const options = {
  scenarios: {
    browse: p.stages
      ? { executor: 'ramping-vus', startVUs: 0, stages: p.stages }
      : { executor: 'constant-vus', vus: p.vus, duration: p.duration },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{name:GET /api/products}': ['p(95)<800'],
    'http_req_duration{name:GET /api/products/{sku}}': ['p(95)<800'],
    'http_req_duration{name:static}': ['p(95)<500'],
  },
};

const CATEGORIES = ['dresses', 'tops', 'bottoms', 'outerwear', 'bags', 'shoes'];

export default function () {
  group('home', () => {
    check(http.get(`${BASE}/`, { tags: { name: 'static' } }), { 'index 200': (r) => r.status === 200 });
    check(http.get(`${BASE}/config.json`, { tags: { name: 'static' } }), { 'config 200': (r) => r.status === 200 });
  });
  let products = [];
  group('catalogue', () => {
    const cat = CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)];
    const all = http.get(`${BASE}/api/products`, { tags: { name: 'GET /api/products' } });
    check(all, { 'products 200': (r) => r.status === 200 });
    products = all.status === 200 ? all.json() : [];
    http.get(`${BASE}/api/products?category=${cat}`, { tags: { name: 'GET /api/products' } });
  });
  sleep(1 + Math.random() * 2);
  if (products.length) {
    group('details', () => {
      const pick = products[Math.floor(Math.random() * products.length)];
      const r = http.get(`${BASE}/api/products/${encodeURIComponent(pick.sku)}`, { tags: { name: 'GET /api/products/{sku}' } });
      check(r, { 'details 200': (x) => x.status === 200, 'has stock': (x) => typeof x.json('stock') === 'number' });
      if (pick.image_url) http.get(`${BASE}${pick.image_url}`, { tags: { name: 'static' } });
    });
  }
  sleep(1 + Math.random() * 3);
}
