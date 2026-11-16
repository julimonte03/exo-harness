import { useState, type ReactNode } from 'react';
import { Link, NavLink } from 'react-router';
import type { Cart } from '@/hooks/useCart';
import { CartDrawer } from './CartDrawer';

interface LayoutProps {
  cart: Cart;
  children: ReactNode;
}

export function Layout({ cart, children }: LayoutProps) {
  const [cartOpen, setCartOpen] = useState(false);

  return (
    <div className="layout">
      <header className="layout__header">
        <Link to="/" className="layout__brand">
          Node Shop
        </Link>
        <nav>
          <NavLink to="/">Catalog</NavLink>
          <NavLink to="/checkout">Checkout</NavLink>
        </nav>
        <button type="button" onClick={() => setCartOpen(true)}>
          Cart ({cart.count})
        </button>
      </header>
      <main>{children}</main>
      <CartDrawer cart={cart} open={cartOpen} onClose={() => setCartOpen(false)} />
      <footer className="layout__footer">Questions? Write to support@example.com</footer>
    </div>
  );
}
