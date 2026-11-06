import type { Cart, CheckoutStatus, LineItem, Order, Product } from '../types';
import type { Request } from './client';

/** Typed endpoints matching contracts/openapi.yaml. */
export function createApi(request: Request) {
  return {
    products: (category?: string) =>
      request<Product[]>(`/products${category ? `?category=${encodeURIComponent(category)}` : ''}`),
    product: (sku: string) => request<Product>(`/products/${encodeURIComponent(sku)}`),
    cart: () => request<Cart>('/cart', { auth: true }),
    saveCart: (items: LineItem[]) => request<Cart>('/cart', { method: 'PUT', body: { items }, auth: true }),
    checkout: (idempotencyKey: string) =>
      request<CheckoutStatus>('/checkouts', {
        method: 'POST',
        auth: true,
        headers: { 'Idempotency-Key': idempotencyKey },
      }),
    checkoutStatus: (id: string) => request<CheckoutStatus>(`/checkouts/${id}`, { auth: true }),
    orders: () => request<Order[]>('/orders', { auth: true }),
    order: (id: number | string) => request<Order>(`/orders/${id}`, { auth: true }),
  };
}

export type Api = ReturnType<typeof createApi>;
