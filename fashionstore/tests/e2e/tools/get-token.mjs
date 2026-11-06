#!/usr/bin/env node
/**
 * Gets real Cognito tokens for a test shopper the same way the storefront does:
 * authorization code + PKCE through the hosted UI, in headless Chromium.
 * (USER_PASSWORD_AUTH tokens would not carry the fashionstore-api/* scopes.)
 *
 *   node tools/get-token.mjs <storefront_url> <email> <password>
 *
 * Reads cognitoDomain/clientId/scopes from <storefront_url>/config.json and
 * prints {"access_token","id_token","expires_in"} as JSON on stdout.
 */
import { chromium } from '@playwright/test';
import { createHash, randomBytes } from 'node:crypto';

const [base, email, password] = process.argv.slice(2);
if (!base || !email || !password) {
  console.error('usage: get-token.mjs <storefront_url> <email> <password>');
  process.exit(2);
}

const cfg = await (await fetch(new URL('/config.json', base))).json();
const redirectUri = new URL('/auth/callback', base).toString();
const verifier = randomBytes(48).toString('base64url');
const state = randomBytes(16).toString('base64url');
const authorize = new URL(`https://${cfg.cognitoDomain}/oauth2/authorize`);
authorize.search = new URLSearchParams({
  response_type: 'code',
  client_id: cfg.clientId,
  redirect_uri: redirectUri,
  scope: cfg.scopes,
  state,
  code_challenge_method: 'S256',
  code_challenge: createHash('sha256').update(verifier).digest('base64url'),
}).toString();

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  let code = null;
  // Catch the redirect back to the storefront; no need to load the SPA.
  await page.route(`${redirectUri}**`, (route) => {
    const u = new URL(route.request().url());
    if (u.searchParams.get('state') === state) code = u.searchParams.get('code');
    return route.fulfill({ status: 200, body: 'ok' });
  });
  await page.goto(authorize.toString());
  // Classic hosted UI renders each field twice (desktop + mobile); use the visible one.
  await page.locator('input[name="username"]:visible').fill(email);
  await page.locator('input[name="password"]:visible').fill(password);
  await page.locator('input[name="signInSubmitButton"]:visible').click();
  await page.waitForURL(`${redirectUri}**`, { timeout: 30_000 });
  if (!code) throw new Error('no authorization code (wrong password, or state mismatch)');

  const res = await fetch(`https://${cfg.cognitoDomain}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code', client_id: cfg.clientId, code,
      redirect_uri: redirectUri, code_verifier: verifier,
    }),
  });
  if (!res.ok) throw new Error(`token endpoint: HTTP ${res.status} ${await res.text()}`);
  const t = await res.json();
  process.stdout.write(JSON.stringify({ access_token: t.access_token, id_token: t.id_token, expires_in: t.expires_in }));
} finally {
  await browser.close();
}
