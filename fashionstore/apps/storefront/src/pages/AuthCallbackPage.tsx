import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { exchangeCode } from '../auth/pkce';
import type { AppConfig } from '../types';

export function AuthCallbackPage({ config }: { config: AppConfig }) {
  const { setTokens } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const once = useRef(false);

  useEffect(() => {
    if (once.current) return; // StrictMode runs effects twice; a code can only be exchanged once
    once.current = true;
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    if (!code || !state) {
      setError(params.get('error_description') ?? 'Missing authorization code');
      return;
    }
    exchangeCode(config, code, state)
      .then(({ tokens, returnTo }) => {
        setTokens(tokens);
        navigate(returnTo, { replace: true });
      })
      .catch((e: Error) => setError(e.message));
  }, [config, navigate, setTokens]);

  return error ? <p className="error">{error}</p> : <p className="muted">Signing you in…</p>;
}
