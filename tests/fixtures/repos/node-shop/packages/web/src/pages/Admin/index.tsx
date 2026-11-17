import { useState } from 'react';
import type { Order, OrderStatus } from '@shop/shared';
import { fetchOrder, updateOrderStatus } from '../../api/client';
import { OrderSummary } from '@/components';

// The API rejects moves that are not allowed; staff see the reason inline.
const STATUSES: OrderStatus[] = ['paid', 'shipped', 'delivered', 'cancelled'];

export default function AdminPage() {
  const [orderId, setOrderId] = useState('');
  const [adminToken, setAdminToken] = useState('');
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  function run(action: () => Promise<Order>) {
    setError(null);
    action().then(setOrder, (err: Error) => setError(err.message));
  }

  return (
    <section>
      <h1>Back office</h1>
      <input aria-label="Order id" value={orderId} onChange={(e) => setOrderId(e.target.value)} />
      <input aria-label="Admin token" type="password" onChange={(e) => setAdminToken(e.target.value)} />
      <button onClick={() => run(() => fetchOrder(orderId))}>Find order</button>
      {error && <p role="alert">{error}</p>}
      {order && <OrderSummary totals={order.totals} />}
      {order &&
        STATUSES.filter((status) => status !== order.status).map((status) => (
          <button key={status} onClick={() => run(() => updateOrderStatus(order.id, status, adminToken))}>
            Mark as {status}
          </button>
        ))}
    </section>
  );
}
