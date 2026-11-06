import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Footer } from '../src/components/Footer';
import { ProductsPage } from '../src/pages/ProductsPage';
import { renderWith } from './helpers';

describe('Footer', () => {
  it('shows which pilot API version answered', async () => {
    render(renderWith(<Footer />, { version: vi.fn().mockResolvedValue({ version: 'v2' }) }));
    expect(await screen.findByText('API v2')).toBeInTheDocument();
  });

  it('says when the API cannot be reached', async () => {
    render(renderWith(<Footer />, { version: vi.fn().mockRejectedValue(new Error('down')) }));
    expect(await screen.findByText('API unreachable')).toBeInTheDocument();
  });
});

describe('ProductsPage', () => {
  it('filters by category and stock through the catalogue API', async () => {
    const products = vi.fn().mockResolvedValue([]);
    render(renderWith(<ProductsPage />, { products }));
    expect(await screen.findByText('Nothing here yet')).toBeInTheDocument();
    expect(products).toHaveBeenLastCalledWith({ category: undefined, inStock: false });

    await userEvent.click(screen.getByRole('tab', { name: 'bags' }));
    await waitFor(() => expect(products).toHaveBeenLastCalledWith({ category: 'bags', inStock: false }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'In stock only' }));
    await waitFor(() => expect(products).toHaveBeenLastCalledWith({ category: 'bags', inStock: true }));
  });
});
