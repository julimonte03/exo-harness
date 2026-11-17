import { Link } from 'react-router';
import { FREE_SHIPPING_THRESHOLD_CENTS, MAX_QTY_PER_LINE } from '@shop/shared';
import type { Cart } from '@/hooks/useCart';
import { Price } from './Price';

interface CartDrawerProps {
  cart: Cart;
  open: boolean;
  onClose: () => void;
}

export function CartDrawer({ cart, open, onClose }: CartDrawerProps) {
  if (!open) return null;
  const missingForFreeShipping = FREE_SHIPPING_THRESHOLD_CENTS - cart.subtotalCents;
  const empty = cart.items.length === 0;

  return (
    <aside className="cart-drawer" aria-label="Shopping cart">
      <header>
        <h2>Your cart ({cart.count})</h2>
        <button type="button" onClick={onClose} aria-label="Close cart">
          x
        </button>
      </header>
      {empty && <p>Your cart is empty.</p>}
      <ul className="cart-drawer__lines">
        {cart.items.map((item) => (
          <li key={item.productId}>
            <span>{item.name}</span>
            <button
              type="button"
              aria-label={`One less ${item.name}`}
              onClick={() => cart.setQuantity(item.productId, item.quantity - 1)}
            >
              -
            </button>
            <span>{item.quantity}</span>
            <button
              type="button"
              aria-label={`One more ${item.name}`}
              disabled={item.quantity >= MAX_QTY_PER_LINE}
              onClick={() => cart.setQuantity(item.productId, item.quantity + 1)}
            >
              +
            </button>
            <Price cents={item.unitPriceCents * item.quantity} />
            <button type="button" onClick={() => cart.setQuantity(item.productId, 0)}>
              Remove
            </button>
          </li>
        ))}
      </ul>
      {!empty && (
        <footer>
          <p>
            Subtotal: <Price cents={cart.subtotalCents} />
          </p>
          {missingForFreeShipping > 0 && (
            <p className="cart-drawer__hint">
              Add <Price cents={missingForFreeShipping} /> more for free shipping.
            </p>
          )}
          <Link to="/checkout" onClick={onClose}>
            Checkout
          </Link>
        </footer>
      )}
    </aside>
  );
}
