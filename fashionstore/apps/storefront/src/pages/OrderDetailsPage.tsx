import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { formatPrice } from '../config';
import type { Order } from '../types';

export function OrderDetailsPage() {
  const { orderId = '' } = useParams();
  const api = useApi();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.order(orderId).then(setOrder).catch((e: Error) => setError(e.message));
  }, [api, orderId]);

  if (error) return <p className="error">{error}</p>;
  if (!order) return <p className="muted">Loading…</p>;
  return (
    <section>
      <h1>Order #{order.order_id}</h1>
      <p><span className={`badge ${order.status.toLowerCase()}`}>{order.status}</span> {order.reason ?? ''}</p>
      <ul className="cart">
        {order.items.map((i) => (
          <li key={i.sku} className="cart-item">
            <strong>{i.name}</strong>
            <span>× {i.qty}</span>
            <span className="price">{formatPrice(i.unit_price_cents * i.qty)}</span>
          </li>
        ))}
      </ul>
      <p className="total">Total <strong>{formatPrice(order.total_cents)}</strong></p>
    </section>
  );
}
