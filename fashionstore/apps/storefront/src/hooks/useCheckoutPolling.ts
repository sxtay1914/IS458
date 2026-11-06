import { useEffect, useRef, useState } from 'react';
import type { CheckoutStatus } from '../types';

export interface PollingOptions {
  initialDelayMs?: number;
  maxDelayMs?: number;
  timeoutMs?: number;
}

/**
 * Polls GET /api/checkouts/:id until the outcome is CONFIRMED or REJECTED.
 * Backs off 500 ms -> 4 s so a flash-sale backlog does not hammer the API.
 */
export function useCheckoutPolling(
  checkoutId: string | undefined,
  fetchStatus: (id: string) => Promise<CheckoutStatus>,
  { initialDelayMs = 500, maxDelayMs = 4000, timeoutMs = 120_000 }: PollingOptions = {},
) {
  const [status, setStatus] = useState<CheckoutStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const fetchRef = useRef(fetchStatus);
  fetchRef.current = fetchStatus;

  useEffect(() => {
    if (!checkoutId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    let delay = initialDelayMs;

    const tick = async () => {
      try {
        const s = await fetchRef.current(checkoutId);
        if (cancelled) return;
        setStatus(s);
        setError(null);
        if (s.status !== 'PENDING') return;
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message);
      }
      if (Date.now() - started >= timeoutMs) {
        setTimedOut(true);
        return;
      }
      timer = setTimeout(tick, delay);
      delay = Math.min(delay * 2, maxDelayMs);
    };
    void tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [checkoutId, initialDelayMs, maxDelayMs, timeoutMs]);

  return { status, error, timedOut, done: status !== null && status.status !== 'PENDING' };
}
