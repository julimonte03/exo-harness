'use strict';

const { Router } = require('express');
const { availableFor, stockLevel } = require('../inventory/stock');

module.exports = function productsRouter({ db }) {
  return Router().get('/', async (req, res) => {
    const products = await db.products.all();
    const available = await availableFor(db, products.map((p) => p.id));
    res.json(
      products.map(({ id, name, price_cents: priceCents }) => {
        const left = available.get(id);
        return { id, name, priceCents, available: left, stock: stockLevel(left) };
      }),
    );
  });
};
