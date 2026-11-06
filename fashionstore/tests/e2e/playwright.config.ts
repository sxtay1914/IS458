import { defineConfig, devices } from '@playwright/test';

/**
 * Two ways to run the same specs:
 *  - mock (default): builds the storefront, serves it with `vite preview` and
 *    fakes Cognito and /api/** in the browser (support/mock-backend.ts).
 *    No AWS needed; runs in CI.
 *  - live: E2E_BASE_URL=https://dxxxx.cloudfront.net plus test users
 *    (E2E_USER_EMAIL / E2E_USER_PASSWORD, E2E_DECLINE_EMAIL / E2E_DECLINE_PASSWORD).
 *    Signs in through the real Cognito hosted UI and hits the real API.
 */
const live = !!process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: './specs',
  timeout: live ? 180_000 : 30_000,
  expect: { timeout: live ? 120_000 : 5_000 },
  fullyParallel: !live,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4173',
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: live ? 'live' : 'mock', use: { ...devices['Desktop Chrome'] } }],
  webServer: live
    ? undefined
    : {
        command: 'npm --prefix ../../apps/storefront run build && npm --prefix ../../apps/storefront run preview',
        url: 'http://localhost:4173',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
