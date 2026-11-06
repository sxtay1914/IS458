import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { AppConfig } from '../types';
import { buildAuthorizeUrl, decodeJwt, logoutUrl, type TokenSet } from './pkce';

const TOKENS_KEY = 'fs.tokens';

export interface User {
  sub: string;
  email: string;
}

interface AuthState {
  user: User | null;
  accessToken: () => string | null;
  login: (returnTo?: string) => Promise<void>;
  logout: () => void;
  setTokens: (t: TokenSet) => void;
}

const Ctx = createContext<AuthState | null>(null);

function readTokens(): TokenSet | null {
  try {
    const raw = sessionStorage.getItem(TOKENS_KEY);
    if (!raw) return null;
    const t = JSON.parse(raw) as TokenSet;
    return t.expires_at > Date.now() + 30_000 ? t : null;
  } catch {
    return null;
  }
}

function userFrom(t: TokenSet | null): User | null {
  if (!t) return null;
  const claims = decodeJwt(t.id_token);
  return { sub: String(claims.sub ?? ''), email: String(claims.email ?? '') };
}

export function AuthProvider({ config, children }: { config: AppConfig; children: ReactNode }) {
  const [tokens, setTokensState] = useState<TokenSet | null>(readTokens);

  const setTokens = useCallback((t: TokenSet) => {
    sessionStorage.setItem(TOKENS_KEY, JSON.stringify(t));
    setTokensState(t);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user: userFrom(tokens),
      accessToken: () => readTokens()?.access_token ?? null,
      login: async (returnTo = window.location.pathname) => {
        window.location.assign(await buildAuthorizeUrl(config, returnTo));
      },
      logout: () => {
        sessionStorage.removeItem(TOKENS_KEY);
        setTokensState(null);
        window.location.assign(logoutUrl(config));
      },
      setTokens,
    }),
    [tokens, config, setTokens],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthProvider');
  return v;
}
