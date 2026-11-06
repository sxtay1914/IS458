import { expect, type Page } from '@playwright/test';
import { live, type Shopper } from './env';
import { installMockBackend, type MockState } from './mock-backend';

/** Mock mode: install the fake backend for this shopper. Live mode: no-op. */
export async function prepare(page: Page, who: Shopper): Promise<MockState | null> {
  return live ? null : installMockBackend(page, who.email);
}

/**
 * Completes the hosted-UI sign-in that the storefront started (PKCE).
 * The classic Cognito hosted UI renders each field twice (desktop + mobile
 * layouts); only one copy is visible.
 */
export async function completeSignIn(page: Page, who: Shopper) {
  if (live) {
    await page.waitForURL(/\/(login|oauth2\/authorize)/);
    await page.locator('input[name="username"]:visible').fill(who.email);
    await page.locator('input[name="password"]:visible').fill(who.password);
    await page.locator('input[name="signInSubmitButton"]:visible').click();
  }
  await page.waitForURL((u) => !u.pathname.startsWith('/auth/callback') && !u.hostname.includes('cognito') && !u.hostname.includes('amazoncognito'));
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
}

/** Empties the shopper's server-side cart so live runs start clean. */
export async function emptyCart(page: Page) {
  await page.goto('/cart');
  for (;;) {
    const dec = page.getByRole('button', { name: /^Decrease / }).first();
    if (!(await dec.isVisible().catch(() => false))) break;
    await dec.click();
    await page.waitForTimeout(200);
  }
}
