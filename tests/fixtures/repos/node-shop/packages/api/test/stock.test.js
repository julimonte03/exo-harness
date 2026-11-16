const { availableFor, stockLevel } = require('../src/inventory/stock');
const { validateOrderLines } = require('../src/orders/rules');

const mug = { id: 'mug-classic', price_cents: 1250, on_hand: 6 };
const order = (status, quantity) => ({ status, lines: [{ productId: mug.id, quantity }] });
const orders = [order('pending', 2), order('paid', 1), order('cancelled', 3)];
const db = {
  products: { byIds: async () => [mug] },
  orders: { withStatus: async (statuses) => orders.filter((o) => statuses.includes(o.status)) },
};

test('pending and paid orders hold stock, cancelled ones do not', async () => {
  expect((await availableFor(db, [mug.id])).get(mug.id)).toBe(3);
});

test('five units or fewer is low stock', () => {
  expect([0, 5, 6].map(stockLevel)).toEqual(['out-of-stock', 'low-stock', 'in-stock']);
});

test('a line takes 1 to 10 units and never more than what is available', () => {
  const products = new Map([[mug.id, mug]]);
  const check = (quantity, available) => () =>
    validateOrderLines([{ productId: mug.id, quantity }], products, new Map([[mug.id, available]]));
  expect(check(4, 3)).toThrow('Only 3 left of mug-classic');
  expect(check(11, 50)).toThrow('between 1 and 10');
});
