import { useEffect, useState } from 'react';
import { MAX_CART_LINES, MAX_QTY_PER_LINE, subtotalCents } from '@shop/shared';
import type { CartLine, Product } from '@shop/shared';

const STORAGE_KEY = 'node-shop.cart';

export type CartItem = CartLine & { name: string };
export type Cart = ReturnType<typeof useCart>;

/** Same limits as the API: 10 units per line, 25 lines, and zero removes the line. */
export function applyQuantity(items: CartItem[], item: CartItem): CartItem[] {
  const exists = items.some((line) => line.productId === item.productId);
  if (item.quantity <= 0) return items.filter((line) => line.productId !== item.productId);
  if (!exists && items.length >= MAX_CART_LINES) return items;
  const next = { ...item, quantity: Math.min(item.quantity, MAX_QTY_PER_LINE) };
  if (!exists) return [...items, next];
  return items.map((line) => (line.productId === item.productId ? next : line));
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>(
    () => JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as CartItem[],
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  return {
    items,
    count: items.reduce((sum, line) => sum + line.quantity, 0),
    subtotalCents: subtotalCents(items),
    add: ({ id, name, priceCents }: Product, quantity = 1) =>
      setItems((current) => {
        const total = (current.find((line) => line.productId === id)?.quantity ?? 0) + quantity;
        return applyQuantity(current, { productId: id, name, unitPriceCents: priceCents, quantity: total });
      }),
    setQuantity: (productId: string, quantity: number) =>
      setItems((current) => {
        const existing = current.find((line) => line.productId === productId);
        return existing ? applyQuantity(current, { ...existing, quantity }) : current;
      }),
    clear: () => setItems([]),
  };
}
