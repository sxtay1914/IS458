import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../src/api/client';
import { CheckoutPage } from '../src/pages/CheckoutPage';
import { renderWith, signIn } from './helpers';

const cart = { items: [{ sku: 'BAG-001', qty: 2 }], total_cents: 13980 };

describe('CheckoutPage', () => {
  it('retries a failed checkout with the same Idempotency-Key, then shows the status page', async () => {
    signIn();
    const checkout = vi.fn()
      .mockRejectedValueOnce(new ApiError(503, 'HTTP_503', 'Service busy'))
      .mockResolvedValue({ checkout_id: 'c-1', status: 'PENDING', reason: null, order_id: null });
    render(renderWith(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/checkout/:id" element={<p>status page</p>} />
      </Routes>,
      { cart: vi.fn().mockResolvedValue(cart), checkout },
      '/checkout',
    ));

    expect(await screen.findByText('S$139.80')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Place order' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Service busy');
    await userEvent.click(screen.getByRole('button', { name: 'Retry checkout' }));

    await waitFor(() => expect(screen.getByText('status page')).toBeInTheDocument());
    expect(checkout).toHaveBeenCalledTimes(2);
    expect(checkout.mock.calls[0][0]).toBe(checkout.mock.calls[1][0]);
    expect(sessionStorage.getItem('fs.checkout.idempotencyKey')).toBeNull();
  });

  it('recovers a lost response after refresh even when the server cart is empty', async () => {
    signIn();
    const checkout = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValue({ checkout_id: 'c-1', status: 'PENDING', reason: null, order_id: null });
    const first = render(renderWith(<CheckoutPage />, { cart: vi.fn().mockResolvedValue(cart), checkout }, '/checkout'));
    await screen.findByText('S$139.80');
    await userEvent.click(screen.getByRole('button', { name: 'Place order' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to fetch');
    const key = checkout.mock.calls[0][0];
    first.unmount();

    render(renderWith(
      <Routes>
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/checkout/:id" element={<p>status page</p>} />
      </Routes>,
      { cart: vi.fn().mockResolvedValue({ items: [], total_cents: 0 }), checkout },
      '/checkout',
    ));
    await screen.findByText('S$0.00');
    const retry = screen.getByRole('button', { name: 'Retry checkout' });
    expect(retry).toBeEnabled();
    await userEvent.click(retry);

    await screen.findByText('status page');
    expect(checkout).toHaveBeenCalledTimes(2);
    expect(checkout.mock.calls[1][0]).toBe(key);
    expect(sessionStorage.getItem('fs.checkout.idempotencyKey')).toBeNull();
  });

  it('does not start a new checkout with an empty cart', async () => {
    signIn();
    render(renderWith(<CheckoutPage />, { cart: vi.fn().mockResolvedValue({ items: [], total_cents: 0 }) }, '/checkout'));
    await screen.findByText('S$0.00');
    expect(screen.getByRole('button', { name: 'Place order' })).toBeDisabled();
    expect(sessionStorage.getItem('fs.checkout.idempotencyKey')).toBeNull();
  });

  it('asks signed-out shoppers to sign in', () => {
    render(renderWith(<CheckoutPage />, {}, '/checkout'));
    expect(screen.getByRole('button', { name: 'Sign in to check out' })).toBeInTheDocument();
  });
});
