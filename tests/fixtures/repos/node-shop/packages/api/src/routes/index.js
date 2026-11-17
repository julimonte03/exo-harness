'use strict';

const { Router } = require('express');
const productsRouter = require('./products');
const ordersRouter = require('./orders');
const cartRouter = require('./cart');

function buildRouter(deps) {
  const router = Router();
  router.use('/products', productsRouter(deps));
  router.use('/orders', ordersRouter(deps));
  router.use('/carts', cartRouter(deps));
  return router;
}

module.exports = { buildRouter };
