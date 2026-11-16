'use strict';

const { randomUUID } = require('node:crypto');
const inventory = require('../inventory/stock');
const { HttpError } = require('../errors');
const { validateOrderLines } = require('./rules');
const { priceOrder } = require('./totals');
const { assertTransition, needsRefund } = require('./status');

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function createOrderService({ db, taxRate, newId = randomUUID }) {
  async function placeOrder({ email, lines, promoCode } = {}) {
    if (!EMAIL.test(email || '')) throw new HttpError(400, 'A valid email is required');
    const ids = (lines || []).map((line) => line.productId);
    const products = new Map((await db.products.byIds(ids)).map((p) => [p.id, p]));
    const priced = validateOrderLines(lines, products, await inventory.availableFor(db, ids));
    const totals = priceOrder(priced, { promoCode, taxRate });
    const order = { id: newId(), email, status: 'pending', lines: priced, totals };
    await db.orders.insert(order);
    return order;
  }

  async function changeStatus(id, nextStatus) {
    const order = await db.orders.byId(id);
    if (!order) throw new HttpError(404, `Order ${id} not found`);
    assertTransition(order.status, nextStatus);
    if (nextStatus === 'shipped') await inventory.consume(db, order.lines);
    const patch = { status: nextStatus, refund_required: needsRefund(order.status, nextStatus) };
    await db.orders.update(id, patch);
    return { ...order, ...patch };
  }

  return { placeOrder, changeStatus };
}

module.exports = { createOrderService };
