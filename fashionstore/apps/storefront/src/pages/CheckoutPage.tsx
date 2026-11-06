import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
import { CheckoutSteps } from '../components/CheckoutSteps';
import { Icon } from '../components/Icon';
import { formatPrice } from '../config';
import { useCart } from '../hooks/useCart';
import { clearCheckoutKey, currentCheckoutKey, savedCheckoutKey } from './checkoutKey';

export function CheckoutPage() {
  const api = useApi();
  const { user, login } = useAuth();
  const { cart } = useCart();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [checkoutKey, setCheckoutKey] = useState(savedCheckoutKey);

  if (!user) {
    return (
      <section className="empty">
        <div className="bubble bubble-brand" aria-hidden="true"><Icon name="user" size={44} /></div>
        <h1>Almost there</h1>
        <button className="btn btn-primary btn-lg" onClick={() => void login('/checkout')}>Sign in to check out</button>
      </section>
    );
  }

  const place = async () => {
    setBusy(true);
    setError(null);
    try {
      const key = checkoutKey ?? currentCheckoutKey();
      setCheckoutKey(key);
      const res = await api.checkout(key);
      clearCheckoutKey();
      setCheckoutKey(null);
      navigate(`/checkout/${res.checkout_id}`);
    } catch (e) {
      setError((e as Error).message); // key kept: pressing again retries the same checkout
    } finally {
      setBusy(false);
    }
  };

  const count = cart.items.reduce((n, i) => n + i.qty, 0);

  return (
    <section className="narrow">
      <CheckoutSteps current={1} />
      <div className="panel">
        <h1>Checkout</h1>
        <ul className="review-list">
          {cart.items.map((i) => (
            <li key={i.sku}><span>{i.sku}</span><span className="muted">× {i.qty}</span></li>
          ))}
        </ul>
        <p className="summary-row total">
          <span>{count} {count === 1 ? 'item' : 'items'}</span>
          <strong>{formatPrice(cart.total_cents)}</strong>
        </p>
        <p className="note">Payment is simulated for this demo. Confirmation goes to {user.email}.</p>
        {error && <p className="alert alert-bad" role="alert">{error}</p>}
        <button className="btn btn-primary btn-block btn-lg" disabled={busy || (!checkoutKey && cart.items.length === 0)}
                onClick={() => void place()}>
          {busy ? 'Placing order…' : checkoutKey ? 'Retry checkout' : 'Place order'}
        </button>
      </div>
    </section>
  );
}
