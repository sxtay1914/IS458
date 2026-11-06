import { useEffect, useState } from 'react';
import { useApi } from '../api/ApiContext';
import { Icon } from '../components/Icon';
import { ProductCard } from '../components/ProductCard';
import type { Product } from '../types';

const CATEGORIES = ['all', 'dresses', 'tops', 'bottoms', 'outerwear', 'bags', 'shoes'];

export function ProductsPage() {
  const api = useApi();
  const [category, setCategory] = useState('all');
  const [inStock, setInStock] = useState(false);
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setError(null);
    api
      .products({ category: category === 'all' ? undefined : category, inStock })
      .then((p) => live && setProducts(p))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, category, inStock]);

  return (
    <section>
      <div className="hero">
        <div>
          <p className="eyebrow"><Icon name="bolt" size={16} /> Fresh drop</p>
          <h1>New in</h1>
          <p className="hero-sub">Pick a vibe, tap a piece, and it is in your bag in two taps.</p>
        </div>
        <div className="hero-blobs" aria-hidden="true"><span /><span /><span /></div>
      </div>

      <div className="toolbar">
        <div className="filters" role="tablist" aria-label="Categories">
          {CATEGORIES.map((c) => (
            <button key={c} role="tab" aria-selected={c === category} className={`chip${c === category ? ' active' : ''}`}
                    onClick={() => setCategory(c)}>
              {c}
            </button>
          ))}
        </div>
        <label className="switch">
          <input type="checkbox" checked={inStock} onChange={(e) => setInStock(e.target.checked)} />
          <span className="switch-track" aria-hidden="true"><span className="switch-thumb" /></span>
          In stock only
        </label>
      </div>

      {error && <p className="alert alert-bad">{error}</p>}
      {!products && !error && (
        <div className="grid" aria-busy="true" aria-label="Loading products">
          {Array.from({ length: 8 }, (_, i) => <div key={i} className="card skeleton" />)}
        </div>
      )}
      {products?.length === 0 && (
        <div className="empty">
          <div className="bubble bubble-muted" aria-hidden="true"><Icon name="search" size={40} /></div>
          <h2>Nothing here yet</h2>
          <p className="muted">Try another category{inStock ? ' or include sold-out pieces' : ''}.</p>
        </div>
      )}
      <div className="grid">
        {products?.map((p) => <ProductCard key={p.sku} product={p} />)}
      </div>
    </section>
  );
}
