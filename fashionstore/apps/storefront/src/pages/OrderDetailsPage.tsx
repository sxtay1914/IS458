import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { formatPrice } from '../config';
import type { Order } from '../types';

const REASONS: Record<string, string> = {
  OUT_OF_STOCK: 'An item sold out before we could reserve it.',
  PAYMENT_DECLINED: 'The payment was declined. You have not been charged.',
  UNKNOWN_SKU: 'An item is no longer available.',
};

export function OrderDetailsPage() {
  const { orderId = '' } = useParams();
  const api = useApi();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.order(orderId).then(setOrder).catch((e: Error) => setError(e.message));
  }, [api, orderId]);

  if (error) return <p className="alert alert-bad">{error}</p>;
  if (!order) return <div className="skeleton row" aria-busy="true" />;
  const ok = order.status === 'CONFIRMED';
  return (
    <section className="narrow">
      <div className="panel">
        <div className="order-head">
          <h1>Order #{order.order_id}</h1>
          <span className={`badge ${ok ? 'badge-ok' : 'badge-bad'} ${order.status.toLowerCase()}`}>{order.status}</span>
        </div>
        <p className="muted small">{new Date(order.created_at).toLocaleString()}</p>
        {order.reason && <p className="alert alert-bad">{REASONS[order.reason] ?? order.reason}</p>}
        <ul className="cart">
          {order.items.map((i) => (
            <li key={i.sku} className="cart-item order-line">
              <span className="cart-item-info">
                <strong>{i.name}</strong>
                <span className="muted small">{i.sku}</span>
              </span>
              <span className="muted">× {i.qty}</span>
              <span className="price">{formatPrice(i.unit_price_cents * i.qty)}</span>
            </li>
          ))}
        </ul>
        <p className="summary-row total">Total <strong>{formatPrice(order.total_cents)}</strong></p>
      </div>
    </section>
  );
}
