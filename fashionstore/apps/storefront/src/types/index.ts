export interface Product {
  sku: string;
  name: string;
  description: string | null;
  category: string;
  colour: string | null;
  size: string | null;
  price_cents: number;
  image_url: string | null;
  stock: number;
}

export interface LineItem {
  sku: string;
  qty: number;
}

export interface Cart {
  items: LineItem[];
  total_cents: number;
}

export type CheckoutState = 'PENDING' | 'CONFIRMED' | 'REJECTED';

export interface CheckoutStatus {
  checkout_id: string;
  status: CheckoutState;
  reason: string | null;
  order_id: number | null;
}

export interface OrderItem {
  sku: string;
  name: string;
  qty: number;
  unit_price_cents: number;
}

export interface Order {
  order_id: number;
  checkout_id: string;
  status: 'CONFIRMED' | 'REJECTED';
  reason: string | null;
  total_cents: number;
  created_at: string;
  items: OrderItem[];
}

export interface AppConfig {
  apiBase: string;
  cognitoDomain: string;
  clientId: string;
  scopes: string;
}
