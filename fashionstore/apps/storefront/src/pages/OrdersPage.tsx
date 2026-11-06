import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { formatPrice } from '../config';
import type { Order } from '../types';

export function OrdersPage() {
  const api = useApi();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.orders().then(setOrders).catch((e: Error) => setError(e.message));
  }, [api]);

  return (
    <section>
      <h1>Your orders</h1>
      {error && <p className="error">{error}</p>}
      {orders?.length === 0 && <p className="muted">No orders yet.</p>}
      <ul className="orders">
        {orders?.map((o) => (
          <li key={o.order_id} data-testid="order-row">
            <Link to={`/orders/${o.order_id}`}>#{o.order_id}</Link>
            <span className={`badge ${o.status.toLowerCase()}`}>{o.status}</span>
            <span>{new Date(o.created_at).toLocaleString()}</span>
            <span className="price">{formatPrice(o.total_cents)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
