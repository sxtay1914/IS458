import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
import { Icon } from '../components/Icon';
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

  if (error && !product) return <p className="alert alert-bad">{error}</p>;
  if (!product) return <div className="details"><div className="skeleton tall" /><div className="skeleton" /></div>;

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

  const soldOut = product.stock <= 0;
  const stockPct = Math.max(4, Math.min(100, (product.stock / 25) * 100));

  return (
    <article>
      <Link to="/" className="back"><Icon name="back" size={18} /> Back to shop</Link>
      <div className="details">
        <div className="details-media"><img src={product.image_url ?? undefined} alt={product.name} /></div>
        <div className="panel details-info">
          <p className="eyebrow">{product.category}</p>
          <h1>{product.name}</h1>
          <p className="price price-lg">{formatPrice(product.price_cents)}</p>
          {product.description && <p>{product.description}</p>}
          <div className="tags">
            {product.colour && <span className="tag">{product.colour}</span>}
            {product.size && <span className="tag">Size {product.size}</span>}
          </div>
          <div className="stock">
            <div className="stock-row">
              <span className="small strong">{soldOut ? 'Out of stock' : product.stock < 10 ? 'Going fast' : 'In stock'}</span>
              <span className="small muted">{soldOut ? '0' : product.stock} available</span>
            </div>
            <div className={`progress ${soldOut ? 'progress-bad' : product.stock < 10 ? 'progress-warn' : 'progress-ok'}`}
                 aria-hidden="true"><span style={{ width: `${soldOut ? 0 : stockPct}%` }} /></div>
          </div>
          {error && <p className="alert alert-bad" role="alert">{error}</p>}
          <button className="btn btn-primary btn-block btn-lg" disabled={soldOut || busy} onClick={() => void onAdd()}>
            {soldOut ? 'Sold out' : user ? 'Add to bag' : 'Sign in to buy'}
          </button>
        </div>
      </div>
    </article>
  );
}
