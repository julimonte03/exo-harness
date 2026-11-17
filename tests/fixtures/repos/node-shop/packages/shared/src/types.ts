export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled';

export interface Product { id: string; name: string; priceCents: number; available: number }

export interface CartLine { productId: string; quantity: number; unitPriceCents: number }

export interface OrderTotals {
  subtotalCents: number;
  discountCents: number;
  shippingCents: number;
  taxCents: number;
  totalCents: number;
}

export interface Order {
  id: string;
  email: string;
  status: OrderStatus;
  lines: CartLine[];
  totals: OrderTotals;
}
