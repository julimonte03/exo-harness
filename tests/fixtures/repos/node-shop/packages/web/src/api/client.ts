import type { Order, OrderStatus, Product } from '@shop/shared';

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = { 'Content-Type': 'application/json', ...init.headers };
  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `Request failed with ${response.status}`);
  return body as T;
}

export type PlaceOrderInput = {
  email: string;
  promoCode?: string;
  lines: { productId: string; quantity: number }[];
};

export const fetchProducts = (signal?: AbortSignal) => request<Product[]>('/products', { signal });

export const fetchOrder = (id: string) => request<Order>(`/orders/${encodeURIComponent(id)}`);

export const placeOrder = (input: PlaceOrderInput) =>
  request<Order>('/orders', { method: 'POST', body: JSON.stringify(input) });

export const updateOrderStatus = (id: string, status: OrderStatus, adminToken: string) =>
  request<Order>(`/orders/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    headers: { 'x-admin-token': adminToken },
    body: JSON.stringify({ status }),
  });
