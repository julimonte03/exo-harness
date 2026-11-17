'use strict';

const { LOW_STOCK_THRESHOLD } = require('@shop/shared');
const { OPEN_STATUSES } = require('../orders/status');

/** Available = on hand minus what open orders (pending, paid) hold, never below zero. */
async function availableFor(db, productIds) {
  const [products, openOrders] = await Promise.all([
    db.products.byIds(productIds),
    db.orders.withStatus(OPEN_STATUSES),
  ]);
  const reserved = new Map();
  for (const line of openOrders.flatMap((order) => order.lines)) {
    reserved.set(line.productId, (reserved.get(line.productId) || 0) + line.quantity);
  }
  return new Map(
    products.map((p) => [p.id, Math.max(0, p.on_hand - (reserved.get(p.id) || 0))]),
  );
}

function stockLevel(available) {
  if (!available) return 'out-of-stock';
  return available <= LOW_STOCK_THRESHOLD ? 'low-stock' : 'in-stock';
}

/** Shipping takes the units out of the warehouse; the reservation ends with it. */
async function consume(db, lines) {
  for (const line of lines) await db.products.decrement(line.productId, line.quantity);
}

module.exports = { availableFor, stockLevel, consume };
