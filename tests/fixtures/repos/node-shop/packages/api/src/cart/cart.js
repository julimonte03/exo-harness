'use strict';

const { MAX_CART_LINES, MAX_QTY_PER_LINE } = require('@shop/shared');
const { HttpError } = require('../errors');

const CART_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const toJSON = (cart) => ({
  id: cart?.id,
  lines: [...(cart?.lines ?? [])].map(([productId, quantity]) => ({ productId, quantity })),
});

/** Guest carts live in memory and expire after a week without changes. */
function createCartStore({ now = Date.now } = {}) {
  const carts = new Map();

  function find(cartId) {
    const cart = carts.get(cartId);
    if (cart && now() - cart.updatedAt > CART_TTL_MS) carts.delete(cartId);
    return carts.get(cartId);
  }

  function setQuantity(cartId, productId, quantity) {
    if (!Number.isInteger(quantity) || quantity < 0) throw new HttpError(400, 'Invalid quantity');
    const cart = find(cartId) || { id: cartId, lines: new Map() };
    if (quantity === 0) {
      cart.lines.delete(productId);
    } else if (!cart.lines.has(productId) && cart.lines.size >= MAX_CART_LINES) {
      throw new HttpError(422, `A cart holds at most ${MAX_CART_LINES} products`);
    } else {
      cart.lines.set(productId, Math.min(quantity, MAX_QTY_PER_LINE));
    }
    carts.set(cartId, Object.assign(cart, { updatedAt: now() }));
    return toJSON(cart);
  }

  const addItem = (cartId, productId, quantity = 1) =>
    setQuantity(cartId, productId, (find(cartId)?.lines.get(productId) || 0) + quantity);

  return { get: (cartId) => toJSON(find(cartId)), addItem, setQuantity };
}

module.exports = { CART_TTL_MS, createCartStore };
