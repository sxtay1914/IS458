import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
import { CartItem } from '../components/CartItem';
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
      <section>
        <h1>Your bag</h1>
        <button className="primary" onClick={() => void login('/cart')}>Sign in to see your bag</button>
      </section>
    );
  }

  return (
    <section>
      <h1>Your bag</h1>
      {error && <p className="error">{error}</p>}
      {cart.items.length === 0 ? (
        <p className="muted">Your bag is empty. <Link to="/">Start shopping</Link></p>
      ) : (
        <>
          <ul className="cart">
            {cart.items.map((i) => (
              <CartItem key={i.sku} item={i} product={products[i.sku]} onQty={(q) => void setQty(i.sku, q)} />
            ))}
          </ul>
          <p className="total">Total <strong data-testid="cart-total">{formatPrice(cart.total_cents)}</strong></p>
          <Link className="primary button" to="/checkout">Checkout</Link>
        </>
      )}
    </section>
  );
}
