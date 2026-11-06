import { Link } from 'react-router-dom';
import { formatPrice } from '../config';
import type { Product } from '../types';

export function ProductCard({ product }: { product: Product }) {
  const soldOut = product.stock <= 0;
  return (
    <Link to={`/products/${encodeURIComponent(product.sku)}`} className="card" data-testid="product-card">
      <img src={product.image_url ?? undefined} alt={product.name} loading="lazy" />
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="muted">
          {[product.colour, product.size].filter(Boolean).join(' · ')}
        </p>
        <p className="price">{formatPrice(product.price_cents)}</p>
        {soldOut ? (
          <span className="badge sold-out">Sold out</span>
        ) : product.stock < 10 ? (
          <span className="badge low">Only {product.stock} left</span>
        ) : null}
      </div>
    </Link>
  );
}
