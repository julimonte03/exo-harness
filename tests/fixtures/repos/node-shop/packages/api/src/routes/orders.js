'use strict';

const { Router } = require('express');
const { HttpError } = require('../errors');
const { createOrderService } = require('../orders/service');
const { ORDER_STATUSES } = require('../orders/status');

module.exports = function ordersRouter({ db, config }) {
  const router = Router();
  const orders = createOrderService({ db, taxRate: config.taxRate });

  // Back office only: the token is configured through ADMIN_API_TOKEN.
  function requireAdmin(req, res, next) {
    const ok = Boolean(config.adminToken) && req.get('x-admin-token') === config.adminToken;
    next(ok ? undefined : new HttpError(401, 'Admin token required'));
  }

  router.post('/', async (req, res) => res.status(201).json(await orders.placeOrder(req.body)));

  router.get('/:id', async (req, res) => {
    const order = await db.orders.byId(req.params.id);
    if (!order) throw new HttpError(404, 'Order not found');
    res.json(order);
  });

  router.patch('/:id/status', requireAdmin, async (req, res) => {
    const { status } = req.body;
    if (!ORDER_STATUSES.includes(status)) throw new HttpError(400, `Unknown status ${status}`);
    res.json(await orders.changeStatus(req.params.id, status));
  });

  return router;
};
