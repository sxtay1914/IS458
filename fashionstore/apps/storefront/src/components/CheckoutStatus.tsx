import { Link } from 'react-router-dom';
import type { CheckoutStatus as Status } from '../types';
import { CheckoutSteps } from './CheckoutSteps';
import { Icon } from './Icon';

const REASONS: Record<string, string> = {
  OUT_OF_STOCK: 'An item sold out before we could reserve it.',
  PAYMENT_DECLINED: 'Your payment was declined.',
  UNKNOWN_SKU: 'An item is no longer available.',
};

export function CheckoutStatus({ status, timedOut }: { status: Status | null; timedOut?: boolean }) {
  if (!status || status.status === 'PENDING') {
    return (
      <div className="status-card pending" role="status">
        <CheckoutSteps current={2} />
        <div className="bubble bubble-wait" aria-hidden="true">
          <span className="dots"><i /><i /><i /></span>
        </div>
        <h2>Placing your order…</h2>
        <div className="progress progress-indeterminate" aria-hidden="true"><span /></div>
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
      <div className="status-card confirmed celebrate" role="status">
        <CheckoutSteps current={3} />
        <div className="bubble bubble-ok pop" aria-hidden="true"><Icon name="check" size={56} /></div>
        <h2>Order confirmed</h2>
        <p>Order #{status.order_id}. A confirmation email is on its way.</p>
        <div className="actions">
          <Link className="btn btn-success" to={`/orders/${status.order_id}`}>View order</Link>
          <Link className="btn btn-ghost" to="/">Keep shopping</Link>
        </div>
      </div>
    );
  }
  return (
    <div className="status-card rejected" role="status">
      <CheckoutSteps current={3} failed />
      <div className="bubble bubble-bad shake" aria-hidden="true"><Icon name="cross" size={52} /></div>
      <h2>We couldn't complete your order</h2>
      <p>{REASONS[status.reason ?? ''] ?? 'The order could not be processed.'} You have not been charged.</p>
      <div className="actions">
        <Link className="btn btn-primary" to="/">Continue shopping</Link>
      </div>
    </div>
  );
}
