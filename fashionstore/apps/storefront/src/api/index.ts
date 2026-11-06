import type { Cart, CheckoutStatus, LineItem, Order, Product } from '../types';
import type { Request } from './client';

export interface ProductQuery {
  category?: string;
  inStock?: boolean;
}

/** Typed endpoints matching contracts/openapi.yaml (every path is covered; see tests/contract.test.ts). */
export function createApi(request: Request) {
  return {
    products: (query: ProductQuery | string = {}) => {
      const q = typeof query === 'string' ? { category: query } : query;
      const params = new URLSearchParams();
      if (q.category) params.set('category', q.category);
      if (q.inStock) params.set('in_stock', 'true');
      const qs = params.toString();
      return request<Product[]>(`/products${qs ? `?${qs}` : ''}`);
    },
    product: (sku: string) => request<Product>(`/products/${encodeURIComponent(sku)}`),
    cart: () => request<Cart>('/cart', { auth: true }),
    saveCart: (items: LineItem[]) => request<Cart>('/cart', { method: 'PUT', body: { items }, auth: true }),
    checkout: (idempotencyKey: string) =>
      request<CheckoutStatus>('/checkouts', {
        method: 'POST',
        auth: true,
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
    checkoutStatus: (id: string) => request<CheckoutStatus>(`/checkouts/${encodeURIComponent(id)}`, { auth: true }),
    orders: () => request<Order[]>('/orders', { auth: true }),
    order: (id: number | string) => request<Order>(`/orders/${encodeURIComponent(String(id))}`, { auth: true }),
    /** Public: which pilot version (v1/v2) served the request; shown in the footer. */
    version: () => request<{ version: string }>('/version'),
  };
}

export type Api = ReturnType<typeof createApi>;
