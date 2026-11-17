'use strict';

const { Router } = require('express');
const { createCartStore } = require('../cart/cart');

module.exports = function cartRouter() {
  const router = Router();
  const carts = createCartStore();
  router.get('/:cartId', (req, res) => res.json(carts.get(req.params.cartId)));
  router.post('/:cartId/items', (req, res) => {
    const { productId, quantity = 1 } = req.body;
    res.status(201).json(carts.addItem(req.params.cartId, productId, quantity));
  });
  router.put('/:cartId/items/:productId', (req, res) => {
    res.json(carts.setQuantity(req.params.cartId, req.params.productId, req.body.quantity));
  });
  return router;
};
