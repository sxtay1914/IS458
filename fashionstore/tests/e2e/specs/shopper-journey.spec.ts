import { expect, test } from '@playwright/test';
import { live, shopper } from '../support/env';
import { completeSignIn, emptyCart, prepare } from '../support/session';

test('browse, sign in with PKCE, buy two bags, see the confirmed order', async ({ page }) => {
  const who = shopper();
  const mock = await prepare(page, who);

  // Browse anonymously: catalogue and category filter are public.
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'New in' })).toBeVisible();
  await page.getByRole('tab', { name: 'bags' }).click();
  await expect(page.getByTestId('product-card')).not.toHaveCount(0);
  await expect(page.getByTestId('product-card').filter({ hasText: 'Linen Midi Dress' })).toHaveCount(0);
  await page.getByTestId('product-card').filter({ hasText: 'Woven Tote Bag' }).click();
  await expect(page).toHaveURL(/\/products\/BAG-001$/);

  // Buying needs an account: the hosted UI round trip returns to this page.
  await page.getByRole('button', { name: 'Sign in to buy' }).click();
  await completeSignIn(page, who);
  await expect(page).toHaveURL(/\/products\/BAG-001$/);
  if (live) {
    await emptyCart(page);
    await page.goto('/products/BAG-001');
  }

  await page.getByRole('button', { name: 'Add to bag' }).click();
  await expect(page).toHaveURL(/\/cart$/);
  await expect(page.getByTestId('cart-total')).toHaveText('S$69.90');
  await page.getByRole('button', { name: 'Increase BAG-001' }).click();
  await expect(page.getByTestId('cart-total')).toHaveText('S$139.80');

  // A hard reload on a deep link must still serve the SPA (CloudFront function / vite preview).
  await page.reload();
  await expect(page.getByTestId('cart-total')).toHaveText('S$139.80');

  await page.getByRole('link', { name: 'Checkout' }).click();
  await page.getByRole('button', { name: 'Place order' }).click();
  await expect(page).toHaveURL(/\/checkout\/[0-9a-f-]{36}$/);
  await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();

  if (mock) {
    expect(mock.checkoutRequests).toHaveLength(1);
    expect(mock.checkoutRequests[0].key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(mock.checkoutRequests[0].authorization).toBe('Bearer mock-access');
  }

  await page.getByRole('link', { name: 'View order' }).click();
  await expect(page.getByRole('heading', { name: /^Order #\d+$/ })).toBeVisible();
  await expect(page.getByText('CONFIRMED')).toBeVisible();
  await expect(page.getByText('S$139.80').last()).toBeVisible();

  await page.getByRole('link', { name: 'Orders' }).click();
  await expect(page.getByTestId('order-row').first()).toContainText('CONFIRMED');
});

test('a checkout that fails to send is retried with the same Idempotency-Key', async ({ page }) => {
  test.skip(live, 'needs a fault-injecting backend; the live equivalent is tests/failure/dispatch-recovery-test.py');
  const who = shopper();
  const mock = (await prepare(page, who))!;
  await page.goto('/products/TOP-002-M');
  await page.getByRole('button', { name: 'Sign in to buy' }).click();
  await completeSignIn(page, who);
  await page.getByRole('button', { name: 'Add to bag' }).click();
  await expect(page.getByTestId('cart-total')).toHaveText('S$39.90');
  await page.getByRole('link', { name: 'Checkout' }).click();

  mock.failNextCheckouts = 1;
  await page.getByRole('button', { name: 'Place order' }).click();
  await expect(page.getByRole('alert')).toContainText('Service busy');
  await page.getByRole('button', { name: 'Retry checkout' }).click();
  await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();

  expect(mock.checkoutRequests).toHaveLength(2);
  expect(mock.checkoutRequests[1].key).toBe(mock.checkoutRequests[0].key);
});
