import { describe, expect, it, vi } from 'vitest';
import { buildAuthorizeUrl, codeChallenge, decodeJwt, exchangeCode } from '../src/auth/pkce';
import { config } from './helpers';

describe('PKCE', () => {
  it('matches the RFC 7636 Appendix B test vector', async () => {
    expect(await codeChallenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk')).toBe(
      'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM',
    );
  });

  it('builds a Cognito authorize URL with S256 and a stored state', async () => {
    const url = new URL(await buildAuthorizeUrl(config, '/cart'));
    expect(url.origin).toBe('https://auth.example.com');
    expect(url.pathname).toBe('/oauth2/authorize');
    expect(url.searchParams.get('code_challenge_method')).toBe('S256');
    expect(url.searchParams.get('client_id')).toBe('client-123');
    expect(url.searchParams.get('response_type')).toBe('code');
    expect(url.searchParams.get('state')).toBe(sessionStorage.getItem('fs.pkce.state'));
    expect(url.searchParams.get('code_challenge')).toBe(
      await codeChallenge(sessionStorage.getItem('fs.pkce.verifier')!),
    );
  });

  it('exchanges the code with the stored verifier and returns to the original page', async () => {
    const url = new URL(await buildAuthorizeUrl(config, '/cart'));
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ access_token: 'a', id_token: 'i', expires_in: 3600 }), { status: 200 }),
    );
    const { tokens, returnTo } = await exchangeCode(config, 'the-code', url.searchParams.get('state')!, fetchMock);
    expect(returnTo).toBe('/cart');
    expect(tokens.access_token).toBe('a');
    const body = fetchMock.mock.calls[0][1].body as URLSearchParams;
    expect(body.get('code_verifier')).toHaveLength(64);
    expect(body.get('grant_type')).toBe('authorization_code');
    expect(sessionStorage.getItem('fs.pkce.verifier')).toBeNull();
  });

  it('rejects a callback whose state does not match (CSRF)', async () => {
    await buildAuthorizeUrl(config, '/');
    await expect(exchangeCode(config, 'c', 'forged', vi.fn())).rejects.toThrow(/state mismatch/);
  });

  it('decodes JWT payloads', () => {
    const bytes = new TextEncoder().encode(JSON.stringify({ sub: 'x', email: 'zoë@example.com' }));
    const payload = btoa(String.fromCharCode(...bytes)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
    expect(decodeJwt(`h.${payload}.s`)).toEqual({ sub: 'x', email: 'zoë@example.com' });
  });
});
