import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
import { CartItem } from '../components/CartItem';
import { CheckoutSteps } from '../components/CheckoutSteps';
import { Icon } from '../components/Icon';
import { formatPrice } from '../config';
import { useCart } from '../hooks/useCart';
import type { Product } from '../types';

export function CartPage() {
  const { user, login } = useAuth();
  const api = useApi();
  const { cart, error, setQty } = useCart();
  const [products, setProducts] = useState<Record<string, Product>>({});

  useEffect(() => {
    api.products().then((ps) => setProducts(Object.fromEntries(ps.map((p) => [p.sku, p])))).catch(() => {});
  }, [api]);

  if (!user) {
    return (
      <section className="empty">
        <div className="bubble bubble-brand" aria-hidden="true"><Icon name="bag" size={44} /></div>
        <h1>Your bag</h1>
        <p className="muted">Sign in and your bag follows you to any device.</p>
        <button className="btn btn-primary btn-lg" onClick={() => void login('/cart')}>Sign in to see your bag</button>
      </section>
    );
  }

  const count = cart.items.reduce((n, i) => n + i.qty, 0);

  return (
    <section>
      <CheckoutSteps current={0} />
      <h1>Your bag</h1>
      {error && <p className="alert alert-bad">{error}</p>}
      {cart.items.length === 0 ? (
        <div className="empty">
          <div className="bubble bubble-muted" aria-hidden="true"><Icon name="bag" size={44} /></div>
          <p className="muted">Your bag is empty.</p>
          <Link className="btn btn-primary" to="/">Start shopping</Link>
        </div>
      ) : (
        <div className="cart-layout">
          <ul className="cart panel">
            {cart.items.map((i) => (
              <CartItem key={i.sku} item={i} product={products[i.sku]} onQty={(q) => void setQty(i.sku, q)} />
            ))}
          </ul>
          <aside className="panel summary">
            <p className="summary-row muted"><span>Items</span><span>{count}</span></p>
            <p className="summary-row total">Total <strong data-testid="cart-total">{formatPrice(cart.total_cents)}</strong></p>
            <Link className="btn btn-primary btn-block btn-lg" to="/checkout">Checkout</Link>
          </aside>
        </div>
      )}
    </section>
  );
}
