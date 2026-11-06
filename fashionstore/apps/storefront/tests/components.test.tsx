import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { CheckoutStatus } from '../src/components/CheckoutStatus';
import { ProductCard } from '../src/components/ProductCard';
import type { Product } from '../src/types';

const product: Product = {
  sku: 'FLASH-001', name: 'Flash Sale Blazer', description: null, category: 'outerwear',
  colour: 'black', size: 'M', price_cents: 9990, image_url: '/images/flash-001.svg', stock: 3,
};

describe('ProductCard', () => {
  it('shows price, low-stock and sold-out states', () => {
    const { rerender } = render(<MemoryRouter><ProductCard product={product} /></MemoryRouter>);
    expect(screen.getByText('S$99.90')).toBeInTheDocument();
    expect(screen.getByText('Only 3 left')).toBeInTheDocument();
    rerender(<MemoryRouter><ProductCard product={{ ...product, stock: 0 }} /></MemoryRouter>);
    expect(screen.getByText('Sold out')).toBeInTheDocument();
  });
});

describe('CheckoutStatus', () => {
  it('explains each outcome', () => {
    const { rerender } = render(<MemoryRouter><CheckoutStatus status={null} /></MemoryRouter>);
    expect(screen.getByText('Placing your order…')).toBeInTheDocument();
    rerender(<MemoryRouter><CheckoutStatus status={{ checkout_id: 'c', status: 'CONFIRMED', reason: null, order_id: 12 }} /></MemoryRouter>);
    expect(screen.getByText(/Order #12/)).toBeInTheDocument();
    rerender(<MemoryRouter><CheckoutStatus status={{ checkout_id: 'c', status: 'REJECTED', reason: 'OUT_OF_STOCK', order_id: 13 }} /></MemoryRouter>);
    expect(screen.getByText(/sold out before we could reserve it/)).toBeInTheDocument();
    expect(screen.getByText(/not been charged/)).toBeInTheDocument();
  });
});
