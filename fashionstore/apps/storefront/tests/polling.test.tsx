import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCheckoutPolling } from '../src/hooks/useCheckoutPolling';
import type { CheckoutStatus } from '../src/types';

const pending: CheckoutStatus = { checkout_id: 'c1', status: 'PENDING', reason: null, order_id: null };
const confirmed: CheckoutStatus = { checkout_id: 'c1', status: 'CONFIRMED', reason: null, order_id: 7 };

describe('useCheckoutPolling', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('polls with backoff until the outcome arrives, then stops', async () => {
    const fetchStatus = vi.fn()
      .mockResolvedValueOnce(pending)
      .mockResolvedValueOnce(pending)
      .mockResolvedValue(confirmed);
    const { result } = renderHook(() => useCheckoutPolling('c1', fetchStatus));

    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(result.current.status?.status).toBe('PENDING');
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });   // 2nd poll after 500 ms
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });  // 3rd after 1 s (backoff)
    expect(result.current.status?.status).toBe('CONFIRMED');
    expect(result.current.done).toBe(true);

    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(fetchStatus).toHaveBeenCalledTimes(3);
  });

  it('keeps polling through transient errors and reports a timeout', async () => {
    const fetchStatus = vi.fn().mockRejectedValueOnce(new Error('503')).mockResolvedValue(pending);
    const { result } = renderHook(() =>
      useCheckoutPolling('c1', fetchStatus, { initialDelayMs: 100, maxDelayMs: 100, timeoutMs: 1000 }));
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(result.current.error).toBe('503');
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(result.current.timedOut).toBe(true);
    expect(result.current.error).toBeNull();
  });
});
