const KEY = 'fs.checkout.idempotencyKey';

/**
 * One Idempotency-Key per checkout attempt. It survives a reload or a network
 * retry (so the API never creates two checkouts for one click) and is cleared
 * once the API has accepted the checkout.
 */
export function currentCheckoutKey(): string {
  let key = savedCheckoutKey();
  if (!key) {
    key = crypto.randomUUID();
    sessionStorage.setItem(KEY, key);
  }
  return key;
}

export function savedCheckoutKey(): string | null {
  return sessionStorage.getItem(KEY);
}

export function clearCheckoutKey(): void {
  sessionStorage.removeItem(KEY);
}
