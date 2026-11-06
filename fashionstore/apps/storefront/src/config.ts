import type { AppConfig } from './types';

let cached: AppConfig | null = null;

/** Runtime settings from /config.json, so one build can be deployed anywhere. */
export async function loadConfig(fetchImpl: typeof fetch = fetch): Promise<AppConfig> {
  if (cached) return cached;
  const res = await fetchImpl('/config.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`config.json: HTTP ${res.status}`);
  cached = (await res.json()) as AppConfig;
  return cached;
}

export function setConfigForTests(cfg: AppConfig | null): void {
  cached = cfg;
}

export function formatPrice(cents: number): string {
  return `S$${(cents / 100).toFixed(2)}`;
}
