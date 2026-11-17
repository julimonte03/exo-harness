'use strict';

const { HttpError } = require('../errors');

const ORDER_STATUSES = ['pending', 'paid', 'shipped', 'delivered', 'cancelled'];
// Orders in these states still hold their stock reservation.
const OPEN_STATUSES = ['pending', 'paid'];
// Allowed moves; delivered and cancelled are terminal.
const TRANSITIONS = { pending: ['paid', 'cancelled'], paid: ['shipped', 'cancelled'], shipped: ['delivered'] };

function canTransition(from, to) {
  return (TRANSITIONS[from] || []).includes(to);
}

function assertTransition(from, to) {
  if (!canTransition(from, to)) throw new HttpError(409, `Order cannot move from ${from} to ${to}`);
}

/** Cancelling an order that was already charged needs a refund. */
function needsRefund(from, to) {
  return from === 'paid' && to === 'cancelled';
}

module.exports = { ORDER_STATUSES, OPEN_STATUSES, canTransition, assertTransition, needsRefund };
