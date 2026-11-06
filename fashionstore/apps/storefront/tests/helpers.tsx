import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { ApiProvider } from '../src/api/ApiContext';
import type { Api } from '../src/api';
import { AuthProvider } from '../src/auth/AuthContext';
import type { AppConfig } from '../src/types';

export const config: AppConfig = {
  apiBase: '/api',
  cognitoDomain: 'auth.example.com',
  clientId: 'client-123',
  scopes: 'openid email',
};

function b64url(obj: object) {
  return btoa(JSON.stringify(obj)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
}

export function signIn(sub = 'user-1', email = 'shopper@example.com') {
  const idToken = `${b64url({ alg: 'none' })}.${b64url({ sub, email })}.sig`;
  sessionStorage.setItem(
    'fs.tokens',
    JSON.stringify({ access_token: 'access-abc', id_token: idToken, expires_at: Date.now() + 3_600_000 }),
  );
}

export function renderWith(ui: ReactNode, api: Partial<Api>, path = '/') {
  return (
    <AuthProvider config={config}>
      <ApiProvider apiBase="/api" api={api as Api}>
        <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
      </ApiProvider>
    </AuthProvider>
  );
}
