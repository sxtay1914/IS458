import { Link } from 'react-router-dom';
import { formatPrice } from '../config';
import type { Product } from '../types';

export function ProductCard({ product }: { product: Product }) {
  const soldOut = product.stock <= 0;
  const low = !soldOut && product.stock < 10;
  return (
    <Link to={`/products/${encodeURIComponent(product.sku)}`} className={`card${soldOut ? ' card-soldout' : ''}`}
          data-testid="product-card">
      <div className="card-media">
        <img src={product.image_url ?? undefined} alt={product.name} loading="lazy" />
        {soldOut ? (
          <span className="badge badge-bad sold-out">Sold out</span>
        ) : low ? (
          <span className="badge badge-warn low">Only {product.stock} left</span>
        ) : null}
      </div>
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="muted small">{[product.colour, product.size].filter(Boolean).join(' · ')}</p>
        <p className="price">{formatPrice(product.price_cents)}</p>
      </div>
    </Link>
  );
}
