'use strict';

const express = require('express');
const { buildRouter } = require('./routes');
// TODO(stock-cache): warm availability at boot once the cache lands.
// const { availableFor } = require('./inventory/stock');

function createApp(deps) {
  const app = express();
  app.use(express.json({ limit: '100kb' }));
  app.get('/health', (req, res) => res.json({ ok: true }));
  app.use('/api', buildRouter(deps));
  // Express 5 forwards rejected promises from async handlers here.
  app.use((err, req, res, _next) => {
    const status = err.status || 500;
    if (status >= 500) console.error(err);
    res.status(status).json({ error: status >= 500 ? 'Internal error' : err.message, details: err.details });
  });
  return app;
}

module.exports = { createApp };
