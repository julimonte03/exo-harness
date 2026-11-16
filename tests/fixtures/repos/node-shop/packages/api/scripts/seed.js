'use strict';

const { readConfig } = require('../src/config');
const { createDb } = require('../src/db');

const PRODUCTS = [
  { id: 'mug-classic', name: 'Classic Mug', price_cents: 1250, on_hand: 40 },
  { id: 'tee-logo', name: 'Logo T-Shirt', price_cents: 2000, on_hand: 25 },
  { id: 'cap-navy', name: 'Navy Cap', price_cents: 1800, on_hand: 4 },
];

const db = createDb(readConfig());
db.knex('products').insert(PRODUCTS).onConflict('id').merge().finally(() => db.close());
