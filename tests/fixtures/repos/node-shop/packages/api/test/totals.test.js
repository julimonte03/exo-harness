const { discountFor, priceOrder } = require('../src/orders/totals');

const tees = (quantity) => [{ productId: 'tee-logo', quantity, unitPriceCents: 2000 }];

test('promo codes ignore case and spaces, unknown ones are rejected', () => {
  expect(discountFor(' welcome10 ')).toBe(10);
  expect(() => discountFor('FREEBIE')).toThrow('Unknown promo code FREEBIE');
});

test('discounts above 30 percent are capped', () => {
  expect(priceOrder(tees(3), { promoCode: 'STAFF40', taxRate: 0 }).discountCents).toBe(1800);
});

test('shipping is free from 50 dollars after discount, else 4.99 and never taxed', () => {
  const free = priceOrder(tees(3), { promoCode: 'WELCOME10', taxRate: 0.08 });
  expect(free).toMatchObject({ shippingCents: 0, taxCents: 432, totalCents: 5832 });
  const paid = priceOrder(tees(2), { taxRate: 0.08 });
  expect(paid).toMatchObject({ shippingCents: 499, taxCents: 320, totalCents: 4819 });
});
