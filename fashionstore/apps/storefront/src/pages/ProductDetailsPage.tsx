import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
import { formatPrice } from '../config';
import { useCart } from '../hooks/useCart';
import type { Product } from '../types';

export function ProductDetailsPage() {
  const { sku = '' } = useParams();
  const api = useApi();
  const { user, login } = useAuth();
  const { add } = useCart();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.product(sku).then(setProduct).catch((e: Error) => setError(e.message));
  }, [api, sku]);

  if (error) return <p className="error">{error}</p>;
  if (!product) return <p className="muted">Loading…</p>;

  const onAdd = async () => {
    if (!user) return login(`/products/${sku}`);
    setBusy(true);
    try {
      await add(product.sku, 1);
      navigate('/cart');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="details">
      <img src={product.image_url ?? undefined} alt={product.name} />
      <div>
        <h1>{product.name}</h1>
        <p className="price">{formatPrice(product.price_cents)}</p>
        <p>{product.description}</p>
        <p className="muted">{[product.colour, product.size].filter(Boolean).join(' · ')}</p>
        <button className="primary" disabled={product.stock <= 0 || busy} onClick={() => void onAdd()}>
          {product.stock <= 0 ? 'Sold out' : user ? 'Add to bag' : 'Sign in to buy'}
        </button>
      </div>
    </article>
  );
}
