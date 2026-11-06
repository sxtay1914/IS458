import { describe, expect, it, vi } from 'vitest';
import spec from '../../../contracts/openapi.yaml?raw';
import { createApi } from '../src/api';
import { createClient } from '../src/api/client';

interface Op { method: string; path: string; params: string[]; isPublic: boolean }

/** Minimal reader for the paths section of contracts/openapi.yaml (two-space indented YAML). */
function operations(yaml: string): Op[] {
  const ops: Op[] = [];
  let path = '';
  let op: Op | null = null;
  for (const line of yaml.split('\n')) {
    if (/^components:/.test(line)) break;
    const p = line.match(/^ {2}(\/\S*):\s*$/);
    if (p) { path = p[1]; continue; }
    const m = line.match(/^ {4}(get|put|post|patch|delete):\s*$/);
    if (m) { op = { method: m[1].toUpperCase(), path, params: [], isPublic: false }; ops.push(op); continue; }
    if (!op) continue;
    if (/^ {6}security: \[\]/.test(line)) op.isPublic = true;
    const q = line.match(/name: ([\w-]+), in: query/);
    if (q) op.params.push(q[1]);
  }
  return ops;
}

const toRegex = (template: string) => new RegExp(`^${template.replace(/\{[^}]+\}/g, '[^/?]+')}$`);

describe('API client vs contracts/openapi.yaml', () => {
  it('calls every documented endpoint with the right method, auth and query parameters', async () => {
    const ops = operations(spec);
    expect(ops.length).toBeGreaterThanOrEqual(9);

    const calls: { method: string; url: URL; auth: boolean; headers: Record<string, string> }[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const headers = (init?.headers ?? {}) as Record<string, string>;
      calls.push({ method: init?.method ?? 'GET', url: new URL(String(input), 'http://x'), auth: !!headers.Authorization, headers });
      return new Response('{}', { status: 200 });
    });
    const api = createApi(createClient('/api', () => 'tok', fetchMock as typeof fetch));

    await api.products();
    await api.products({ category: 'bags', inStock: true });
    await api.product('BAG-001');
    await api.cart();
    await api.saveCart([{ sku: 'BAG-001', qty: 1 }]);
    await api.checkout('6f1c2a3e-1111-4222-8333-444455556666');
    await api.checkoutStatus('6f1c2a3e-1111-4222-8333-444455556666');
    await api.orders();
    await api.order(7);
    await api.version();

    const covered = new Set<Op>();
    for (const call of calls) {
      expect(call.url.pathname.startsWith('/api/')).toBe(true);
      const path = call.url.pathname.slice(4);
      const op = ops.find((o) => o.method === call.method && toRegex(o.path).test(path));
      expect(op, `${call.method} ${path} is not in openapi.yaml`).toBeDefined();
      covered.add(op!);
      expect(call.auth, `${call.method} ${op!.path} auth`).toBe(!op!.isPublic);
      for (const key of call.url.searchParams.keys()) expect(op!.params).toContain(key);
      if (op!.method === 'POST' && op!.path === '/checkouts') expect(call.headers['Idempotency-Key']).toBeTruthy();
    }
    const missing = ops.filter((o) => !covered.has(o)).map((o) => `${o.method} ${o.path}`);
    expect(missing).toEqual([]);

    const filtered = calls[1].url.searchParams;
    expect(filtered.get('category')).toBe('bags');
    expect(filtered.get('in_stock')).toBe('true');
  });
});
