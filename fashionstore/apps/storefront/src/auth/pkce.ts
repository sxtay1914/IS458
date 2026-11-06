/**
 * OAuth 2.0 authorization code flow with PKCE (RFC 7636) against the Cognito
 * hosted UI. The SPA is a public client: no client secret anywhere.
 */
import type { AppConfig } from '../types';

const VERIFIER_KEY = 'fs.pkce.verifier';
const STATE_KEY = 'fs.pkce.state';
const RETURN_KEY = 'fs.pkce.return';

export function base64UrlEncode(bytes: Uint8Array): string {
  let bin = '';
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function randomString(byteLength = 32): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

export async function codeChallenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return base64UrlEncode(new Uint8Array(digest));
}

export function redirectUri(): string {
  return `${window.location.origin}/auth/callback`;
}

export async function buildAuthorizeUrl(cfg: AppConfig, returnTo: string): Promise<string> {
  const verifier = randomString(48);
  const state = randomString(16);
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);
  sessionStorage.setItem(RETURN_KEY, returnTo);
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: cfg.clientId,
    redirect_uri: redirectUri(),
    scope: cfg.scopes,
    state,
    code_challenge_method: 'S256',
    code_challenge: await codeChallenge(verifier),
  });
  return `https://${cfg.cognitoDomain}/oauth2/authorize?${params}`;
}

export interface TokenSet {
  access_token: string;
  id_token: string;
  refresh_token?: string;
  expires_at: number; // epoch ms
}

export async function exchangeCode(
  cfg: AppConfig,
  code: string,
  state: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ tokens: TokenSet; returnTo: string }> {
  const expected = sessionStorage.getItem(STATE_KEY);
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!expected || state !== expected || !verifier) {
    throw new Error('Login state mismatch. Please sign in again.');
  }
  const res = await fetchImpl(`https://${cfg.cognitoDomain}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: cfg.clientId,
      code,
      redirect_uri: redirectUri(),
      code_verifier: verifier,
    }),
  });
  if (!res.ok) throw new Error(`Sign-in failed (HTTP ${res.status})`);
  const body = await res.json();
  const returnTo = sessionStorage.getItem(RETURN_KEY) || '/';
  [VERIFIER_KEY, STATE_KEY, RETURN_KEY].forEach((k) => sessionStorage.removeItem(k));
  return {
    tokens: {
      access_token: body.access_token,
      id_token: body.id_token,
      refresh_token: body.refresh_token,
      expires_at: Date.now() + Number(body.expires_in ?? 3600) * 1000,
    },
    returnTo,
  };
}

export function logoutUrl(cfg: AppConfig): string {
  const params = new URLSearchParams({ client_id: cfg.clientId, logout_uri: `${window.location.origin}/` });
  return `https://${cfg.cognitoDomain}/logout?${params}`;
}

/** Decode (not verify) a JWT payload for display; the API verifies tokens. */
export function decodeJwt(token: string): Record<string, unknown> {
  const part = token.split('.')[1] ?? '';
  const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
  return JSON.parse(decodeURIComponent(escape(json)));
}
