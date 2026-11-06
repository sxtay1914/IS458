import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useAuth } from '../auth/AuthContext';
import { createClient } from './client';
import { createApi, type Api } from './index';

const Ctx = createContext<Api | null>(null);

export function ApiProvider({ apiBase, children, api }: { apiBase: string; children: ReactNode; api?: Api }) {
  const auth = useAuth();
  const value = useMemo(() => api ?? createApi(createClient(apiBase, auth.accessToken)), [api, apiBase, auth]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApi(): Api {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApi outside ApiProvider');
  return v;
}
