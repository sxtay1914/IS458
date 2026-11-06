export const live = !!process.env.E2E_BASE_URL;

export interface Shopper {
  email: string;
  password: string;
}

function need(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is required when E2E_BASE_URL is set`);
  return v;
}

/** A shopper whose payments are approved. */
export function shopper(): Shopper {
  return live
    ? { email: need('E2E_USER_EMAIL'), password: need('E2E_USER_PASSWORD') }
    : { email: 'shopper@example.com', password: 'unused' };
}

/** payment-api declines any checkout whose email contains "+decline". */
export function decliningShopper(): Shopper {
  return live
    ? { email: need('E2E_DECLINE_EMAIL'), password: need('E2E_DECLINE_PASSWORD') }
    : { email: 'shopper+decline@example.com', password: 'unused' };
}
