import type { OrderTotals } from '@shop/shared';
import { Price } from './Price';

interface OrderSummaryProps {
  totals: OrderTotals;
  promoCode?: string;
  onPromoCode?: (code: string) => void;
}

export function OrderSummary({ totals, promoCode, onPromoCode }: OrderSummaryProps) {
  const rows: [string, number][] = [
    ['Subtotal', totals.subtotalCents],
    ['Discount', -totals.discountCents],
    ['Shipping', totals.shippingCents],
    ['Tax', totals.taxCents],
  ];

  return (
    <section className="order-summary" aria-label="Order summary">
      <dl>
        {rows
          .filter(([label, cents]) => cents !== 0 || label === 'Shipping')
          .map(([label, cents]) => (
            <div key={label} className="order-summary__row">
              <dt>{label}</dt>
              <dd>{label === 'Shipping' && cents === 0 ? 'Free' : <Price cents={cents} />}</dd>
            </div>
          ))}
        <div className="order-summary__row order-summary__row--total">
          <dt>Total</dt>
          <dd>
            <Price cents={totals.totalCents} />
          </dd>
        </div>
      </dl>
      {onPromoCode && (
        <label>
          Promo code (applied when you place the order)
          <input
            value={promoCode ?? ''}
            placeholder="WELCOME10"
            onChange={(event) => onPromoCode(event.target.value.trim().toUpperCase())}
          />
        </label>
      )}
    </section>
  );
}
