import { describe, expect, it, vi } from 'vitest';
import { ApiError, createClient } from '../src/api/client';

describe('API client', () => {
  it('sends the bearer token on authenticated calls', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"items":[]}', { status: 200 }));
    const request = createClient('/api', () => 'tok', fetchMock);
    await request('/cart', { auth: true });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer tok');
  });

  it('does not call the API when signed out', async () => {
    const fetchMock = vi.fn();
    const request = createClient('/api', () => null, fetchMock);
    await expect(request('/cart', { auth: true })).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('turns API errors into ApiError with the server code', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('{"error":"EMPTY_CART","message":"The cart is empty"}', { status: 400 }),
    );
    const request = createClient('/api', () => 't', fetchMock);
    const err = (await request('/checkouts', { method: 'POST', auth: true }).catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe('EMPTY_CART');
    expect(err.message).toBe('The cart is empty');
  });

  it('serialises JSON bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    await createClient('/api', () => 't', fetchMock)('/cart', { method: 'PUT', body: { items: [] }, auth: true });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe('{"items":[]}');
    expect(init.headers['Content-Type']).toBe('application/json');
  });
});
