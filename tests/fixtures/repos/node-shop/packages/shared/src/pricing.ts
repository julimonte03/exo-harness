import { FLAT_SHIPPING_CENTS, FREE_SHIPPING_THRESHOLD_CENTS, MAX_DISCOUNT_PERCENT } from './limits.ts';
import type { CartLine, OrderTotals } from './types.ts';

/** Rounds half away from zero to whole cents. */
export function roundCents(value: number): number {
  return Math.sign(value) * Math.round(Math.abs(value));
}

export function subtotalCents(lines: CartLine[]): number {
  return lines.reduce((sum, line) => sum + line.unitPriceCents * line.quantity, 0);
}

/** Discounts above the cap are clamped, never rejected. */
export function discountCents(subtotal: number, percent: number): number {
  const capped = Math.min(Math.max(percent, 0), MAX_DISCOUNT_PERCENT);
  return roundCents((subtotal * capped) / 100);
}

/** Shipping is free once the discounted subtotal reaches the threshold. */
export function shippingCents(discountedSubtotal: number): number {
  if (discountedSubtotal <= 0) return 0;
  return discountedSubtotal >= FREE_SHIPPING_THRESHOLD_CENTS ? 0 : FLAT_SHIPPING_CENTS;
}

/** Tax applies to the discounted subtotal only, never to shipping. */
export function computeTotals(lines: CartLine[], percent: number, taxRate: number): OrderTotals {
  const subtotal = subtotalCents(lines);
  const discount = discountCents(subtotal, percent);
  const taxable = subtotal - discount;
  const shipping = shippingCents(taxable);
  const tax = roundCents(taxable * taxRate);
  return {
    subtotalCents: subtotal,
    discountCents: discount,
    shippingCents: shipping,
    taxCents: tax,
    totalCents: taxable + shipping + tax,
  };
}

export function formatCents(cents: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(cents / 100);
}
