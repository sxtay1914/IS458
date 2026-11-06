import { formatPrice } from '../config';
import type { LineItem, Product } from '../types';

interface Props {
  item: LineItem;
  product?: Product;
  onQty: (qty: number) => void;
}

export function CartItem({ item, product, onQty }: Props) {
  return (
    <li className="cart-item" data-testid="cart-item">
      <div className="thumb" aria-hidden="true">
        {product?.image_url ? <img src={product.image_url} alt="" /> : null}
      </div>
      <div className="cart-item-info">
        <strong>{product?.name ?? item.sku}</strong>
        <div className="muted small">{item.sku}</div>
      </div>
      <div className="qty">
        <button className="qty-btn" aria-label={`Decrease ${item.sku}`} onClick={() => onQty(item.qty - 1)}>−</button>
        <span className="qty-value" aria-label="quantity">{item.qty}</span>
        <button className="qty-btn" aria-label={`Increase ${item.sku}`} onClick={() => onQty(item.qty + 1)}
                disabled={item.qty >= 20}>+</button>
      </div>
      <div className="price">{product ? formatPrice(product.price_cents * item.qty) : ''}</div>
    </li>
  );
}
