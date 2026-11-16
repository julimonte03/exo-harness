import { useState } from 'react';
import { Link } from 'react-router';
import { computeTotals, type Order } from '@shop/shared';
import { placeOrder } from '@/api/client';
import { CheckoutForm, OrderSummary } from '@/components';
import type { CheckoutValues } from '@/components/checkoutValidation';
import type { Cart } from '@/hooks/useCart';

// Estimate only: the API applies the real tax rate and the promo code.
const ESTIMATED_TAX_RATE = 0.08;

export default function CheckoutPage({ cart }: { cart: Cart }) {
  const [promoCode, setPromoCode] = useState('');
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (order) return <p>Thanks! Order {order.id} is {order.status}.</p>;
  if (cart.items.length === 0) return <p>Your cart is empty. <Link to="/">Keep shopping</Link></p>;

  // Card data never reaches our API: the payment provider tokenizes it.
  async function submit({ email }: CheckoutValues) {
    setError(null);
    const lines = cart.items.map(({ productId, quantity }) => ({ productId, quantity }));
    try {
      setOrder(await placeOrder({ email: email.trim(), promoCode: promoCode || undefined, lines }));
      cart.clear();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const totals = computeTotals(cart.items, 0, ESTIMATED_TAX_RATE);
  return (
    <section>
      <h1>Checkout</h1>
      <OrderSummary totals={totals} promoCode={promoCode} onPromoCode={setPromoCode} />
      {error && <p role="alert">{error}</p>}
      <CheckoutForm onSubmit={submit} />
    </section>
  );
}
