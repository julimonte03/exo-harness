const { assertTransition, canTransition, needsRefund } = require('../src/orders/status');

test.each([
  ['pending', 'paid'],
  ['paid', 'shipped'],
  ['paid', 'cancelled'],
  ['shipped', 'delivered'],
])('%s -> %s is allowed', (from, to) => expect(canTransition(from, to)).toBe(true));

test('shipped orders can no longer be cancelled and delivered is terminal', () => {
  expect(() => assertTransition('shipped', 'cancelled')).toThrow('cannot move from shipped');
  expect(canTransition('delivered', 'pending')).toBe(false);
});

test('cancelling a paid order requires a refund', () => {
  expect([needsRefund('paid', 'cancelled'), needsRefund('pending', 'cancelled')]).toEqual([true, false]);
});
