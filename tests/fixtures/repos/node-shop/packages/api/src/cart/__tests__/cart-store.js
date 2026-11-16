const { CART_TTL_MS, createCartStore } = require('../cart');

let clock = 0;
const carts = () => createCartStore({ now: () => clock });

test('adding a product twice adds up, capped at 10 per line', () => {
  const store = carts();
  store.addItem('c1', 'mug-classic', 2);
  expect(store.addItem('c1', 'mug-classic', 3).lines).toEqual([{ productId: 'mug-classic', quantity: 5 }]);
  expect(store.addItem('c1', 'mug-classic', 9).lines[0].quantity).toBe(10);
});

test('a quantity of zero removes the line', () => {
  const store = carts();
  store.addItem('c1', 'cap-navy');
  expect(store.setQuantity('c1', 'cap-navy', 0).lines).toEqual([]);
});

test('a cart holds at most 25 distinct products', () => {
  const store = carts();
  for (let i = 0; i < 25; i += 1) store.addItem('c1', `sku-${i}`);
  expect(() => store.addItem('c1', 'sku-25')).toThrow('at most 25 products');
});

test('carts expire after a week without changes', () => {
  const store = carts();
  store.addItem('c1', 'mug-classic');
  clock += CART_TTL_MS + 1;
  expect(store.get('c1').lines).toEqual([]);
});
