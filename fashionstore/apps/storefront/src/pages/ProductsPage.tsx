import { useEffect, useState } from 'react';
import { useApi } from '../api/ApiContext';
import { ProductCard } from '../components/ProductCard';
import type { Product } from '../types';

const CATEGORIES = ['all', 'dresses', 'tops', 'bottoms', 'outerwear', 'bags', 'shoes'];

export function ProductsPage() {
  const api = useApi();
  const [category, setCategory] = useState('all');
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api
      .products(category === 'all' ? undefined : category)
      .then((p) => live && setProducts(p))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [api, category]);

  return (
    <section>
      <h1>New in</h1>
      <div className="filters" role="tablist">
        {CATEGORIES.map((c) => (
          <button key={c} role="tab" aria-selected={c === category} className={c === category ? 'active' : ''}
                  onClick={() => setCategory(c)}>
            {c}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {!products && !error && <p className="muted">Loading…</p>}
      <div className="grid">
        {products?.map((p) => <ProductCard key={p.sku} product={p} />)}
      </div>
    </section>
  );
}
