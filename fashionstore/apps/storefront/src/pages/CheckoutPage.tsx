import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
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
    return <button className="primary" onClick={() => void login('/checkout')}>Sign in to check out</button>;
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

  return (
    <section>
      <h1>Checkout</h1>
      <p>{cart.items.reduce((n, i) => n + i.qty, 0)} items · <strong>{formatPrice(cart.total_cents)}</strong></p>
      <p className="muted">Payment is simulated for this demo. Confirmation goes to {user.email}.</p>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary" disabled={busy || (!checkoutKey && cart.items.length === 0)} onClick={() => void place()}>
        {busy ? 'Placing order…' : checkoutKey ? 'Retry checkout' : 'Place order'}
      </button>
    </section>
  );
}
