import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router';
import { Layout, ProductGrid } from './components';
import { useCart } from '@/hooks/useCart';
import { useProducts } from '@/hooks/useProducts';
import CheckoutPage from '@/pages/CheckoutPage';

// Staff-only screens ship in their own chunk, fetched on the first visit to /admin.
const AdminPage = lazy(() => import('./pages/Admin'));

export default function App() {
  const cart = useCart();
  const products = useProducts();
  return (
    <Layout cart={cart}>
      <Suspense fallback={<p>Loading...</p>}>
        <Routes>
          <Route path="/" element={<ProductGrid state={products} onAdd={cart.add} />} />
          <Route path="/checkout" element={<CheckoutPage cart={cart} />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
