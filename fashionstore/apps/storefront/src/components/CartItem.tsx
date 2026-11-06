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
      <div>
        <strong>{product?.name ?? item.sku}</strong>
        <div className="muted">{item.sku}</div>
      </div>
      <div className="qty">
        <button aria-label={`Decrease ${item.sku}`} onClick={() => onQty(item.qty - 1)}>−</button>
        <span aria-label="quantity">{item.qty}</span>
        <button aria-label={`Increase ${item.sku}`} onClick={() => onQty(item.qty + 1)} disabled={item.qty >= 20}>+</button>
      </div>
      <div className="price">{product ? formatPrice(product.price_cents * item.qty) : ''}</div>
    </li>
  );
}
