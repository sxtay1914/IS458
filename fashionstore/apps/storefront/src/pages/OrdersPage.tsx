import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { Icon } from '../components/Icon';
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
    <section className="narrow">
      <h1>Your orders</h1>
      {error && <p className="alert alert-bad">{error}</p>}
      {!orders && !error && <div className="skeleton row" aria-busy="true" />}
      {orders?.length === 0 && (
        <div className="empty">
          <div className="bubble bubble-muted" aria-hidden="true"><Icon name="box" size={44} /></div>
          <p className="muted">No orders yet.</p>
          <Link className="btn btn-primary" to="/">Start shopping</Link>
        </div>
      )}
      <ul className="orders">
        {orders?.map((o) => (
          <li key={o.order_id} data-testid="order-row">
            <Link to={`/orders/${o.order_id}`} className="order-card">
              <span className={`order-icon ${o.status.toLowerCase()}`} aria-hidden="true">
                <Icon name={o.status === 'CONFIRMED' ? 'check' : 'cross'} size={22} />
              </span>
              <span className="order-main">
                <strong>#{o.order_id}</strong>
                <span className="muted small">{new Date(o.created_at).toLocaleString()}</span>
              </span>
              <span className={`badge ${o.status === 'CONFIRMED' ? 'badge-ok' : 'badge-bad'} ${o.status.toLowerCase()}`}>
                {o.status}
              </span>
              <span className="price">{formatPrice(o.total_cents)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
