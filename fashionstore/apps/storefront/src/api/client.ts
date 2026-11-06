/** Thin fetch wrapper: JSON in/out, bearer token, API error shape {error, message}. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export type TokenGetter = () => string | null;

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
}

export function createClient(apiBase: string, getToken: TokenGetter, fetchImpl: typeof fetch = fetch) {
  return async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers };
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    if (opts.auth) {
      const token = getToken();
      if (!token) throw new ApiError(401, 'UNAUTHENTICATED', 'Please sign in');
      headers.Authorization = `Bearer ${token}`;
    }
    const res = await fetchImpl(`${apiBase}${path}`, {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      throw new ApiError(res.status, data?.error ?? `HTTP_${res.status}`, data?.message ?? res.statusText);
    }
    return data as T;
  };
}

export type Request = ReturnType<typeof createClient>;
