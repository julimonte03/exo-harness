'use strict';

const { MAX_QTY_PER_LINE } = require('@shop/shared');
const { HttpError } = require('../errors');

/** Lines come back priced from the catalog, never with a price sent by the client. */
function validateOrderLines(lines, productsById, availability) {
  if (!Array.isArray(lines) || lines.length === 0) {
    throw new HttpError(400, 'An order needs at least one line');
  }
  const seen = new Set();
  return lines.map(({ productId, quantity }) => {
    const product = productsById.get(productId);
    if (!product) throw new HttpError(404, `Unknown product ${productId}`);
    if (seen.has(productId)) throw new HttpError(400, `Duplicate line for ${productId}`);
    seen.add(productId);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QTY_PER_LINE) {
      throw new HttpError(400, `Quantity of ${productId} must be between 1 and ${MAX_QTY_PER_LINE}`);
    }
    const available = availability.get(productId) ?? 0;
    if (quantity > available) {
      throw new HttpError(409, `Only ${available} left of ${productId}`, { productId, available });
    }
    return { productId, quantity, unitPriceCents: product.price_cents };
  });
}

module.exports = { validateOrderLines };
