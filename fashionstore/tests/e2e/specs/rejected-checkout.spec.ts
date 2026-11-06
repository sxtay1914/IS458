import { expect, test } from '@playwright/test';
import { decliningShopper, live } from '../support/env';
import { completeSignIn, emptyCart, prepare } from '../support/session';

// payment-api declines every checkout whose email contains "+decline".
test('a declined payment shows a clear rejection and no charge', async ({ page }) => {
  const who = decliningShopper();
  await prepare(page, who);

  await page.goto('/products/DRS-001-M');
  await page.getByRole('button', { name: 'Sign in to buy' }).click();
  await completeSignIn(page, who);
  if (live) {
    await emptyCart(page);
    await page.goto('/products/DRS-001-M');
  }
  await page.getByRole('button', { name: 'Add to bag' }).click();
  await page.getByRole('link', { name: 'Checkout' }).click();
  await page.getByRole('button', { name: 'Place order' }).click();

  await expect(page.getByRole('heading', { name: "We couldn't complete your order" })).toBeVisible();
  await expect(page.getByText('Your payment was declined.')).toBeVisible();
  await expect(page.getByText(/not been charged/)).toBeVisible();

  await page.getByRole('link', { name: 'Orders' }).click();
  await expect(page.getByTestId('order-row').first()).toContainText('REJECTED');
});

test('signed-out shoppers are sent to sign in, not shown an error', async ({ page }) => {
  await prepare(page, decliningShopper());
  await page.goto('/cart');
  await expect(page.getByRole('button', { name: 'Sign in to see your bag' })).toBeVisible();
  await page.goto('/checkout');
  await expect(page.getByRole('button', { name: 'Sign in to check out' })).toBeVisible();
});
