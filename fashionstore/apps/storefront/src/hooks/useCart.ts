import { useCallback, useEffect, useState } from 'react';
import { useApi } from '../api/ApiContext';
import { useAuth } from '../auth/AuthContext';
import type { Cart, LineItem } from '../types';

/** Server-side cart (store-api /api/cart) for the signed-in shopper. */
export function useCart() {
  const api = useApi();
  const { user } = useAuth();
  const [cart, setCart] = useState<Cart>({ items: [], total_cents: 0 });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      setCart(await api.cart());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [api, user]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const save = useCallback(
    async (items: LineItem[]) => {
      try {
        setCart(await api.saveCart(items.filter((i) => i.qty > 0)));
        setError(null);
      } catch (e) {
        setError((e as Error).message);
        throw e;
      }
    },
    [api],
  );

  const add = useCallback(
    async (sku: string, qty = 1) => {
      const current = await api.cart();
      const existing = current.items.find((i) => i.sku === sku);
      const items = existing
        ? current.items.map((i) => (i.sku === sku ? { ...i, qty: i.qty + qty } : i))
        : [...current.items, { sku, qty }];
      await save(items);
    },
    [api, save],
  );

  const setQty = useCallback(
    (sku: string, qty: number) => save(cart.items.map((i) => (i.sku === sku ? { ...i, qty } : i))),
    [cart.items, save],
  );

  return { cart, error, loading, reload, add, setQty };
}
