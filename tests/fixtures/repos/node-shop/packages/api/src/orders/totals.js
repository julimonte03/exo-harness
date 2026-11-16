'use strict';

const { computeTotals } = require('@shop/shared');
const { HttpError } = require('../errors');

// Percent off the subtotal. Shared pricing caps every discount at 30%.
const PROMO_CODES = { WELCOME10: 10, VIP25: 25, STAFF40: 40 };

function discountFor(promoCode) {
  if (!promoCode) return 0;
  const percent = PROMO_CODES[String(promoCode).trim().toUpperCase()];
  if (percent === undefined) throw new HttpError(422, `Unknown promo code ${promoCode}`);
  return percent;
}

function priceOrder(lines, { promoCode, taxRate }) {
  return computeTotals(lines, discountFor(promoCode), taxRate);
}

module.exports = { PROMO_CODES, discountFor, priceOrder };
