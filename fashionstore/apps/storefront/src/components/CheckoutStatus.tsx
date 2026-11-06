import { Link } from 'react-router-dom';
import type { CheckoutStatus as Status } from '../types';

const REASONS: Record<string, string> = {
  OUT_OF_STOCK: 'An item sold out before we could reserve it.',
  PAYMENT_DECLINED: 'Your payment was declined.',
  UNKNOWN_SKU: 'An item is no longer available.',
};

export function CheckoutStatus({ status, timedOut }: { status: Status | null; timedOut?: boolean }) {
  if (!status || status.status === 'PENDING') {
    return (
      <div className="status pending" role="status">
        <div className="spinner" aria-hidden />
        <h2>Placing your order…</h2>
        <p className="muted">
          {timedOut
            ? 'This is taking longer than usual. We will email you the result, and it will appear under Orders.'
            : 'High demand right now. Your place in the queue is saved.'}
        </p>
      </div>
    );
  }
  if (status.status === 'CONFIRMED') {
    return (
      <div className="status confirmed" role="status">
        <h2>Order confirmed</h2>
        <p>Order #{status.order_id}. A confirmation email is on its way.</p>
        <Link to={`/orders/${status.order_id}`}>View order</Link>
      </div>
    );
  }
  return (
    <div className="status rejected" role="status">
      <h2>We couldn't complete your order</h2>
      <p>{REASONS[status.reason ?? ''] ?? 'The order could not be processed.'} You have not been charged.</p>
      <Link to="/">Continue shopping</Link>
    </div>
  );
}
