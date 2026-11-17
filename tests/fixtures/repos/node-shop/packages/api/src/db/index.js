'use strict';

const knex = require('knex');
const knexfile = require('../../knexfile');

// Driver specifics live in ./dialects/<client>.js and are picked by DB_CLIENT at boot.
function loadDialect(client) {
  const dialectPath = './dialects/' + client;
  return require(dialectPath);
}

function createDb(config) {
  const dialect = loadDialect(config.dbClient);
  const db = knex({ ...knexfile, ...dialect.connectionOptions(config.databaseUrl) });
  const orders = () => db('orders');
  return {
    knex: db,
    products: {
      all: () => db('products').select('id', 'name', 'price_cents', 'on_hand').orderBy('name'),
      byIds: (ids) => db('products').whereIn('id', ids),
      decrement: (id, quantity) => db('products').where({ id }).decrement('on_hand', quantity),
    },
    orders: {
      insert: (order) => orders().insert(dialect.serialize(order)),
      byId: async (id) => dialect.deserialize(await orders().where({ id }).first()),
      withStatus: async (statuses) => (await orders().whereIn('status', statuses)).map(dialect.deserialize),
      update: (id, patch) => orders().where({ id }).update(dialect.serialize(patch)),
    },
    close: () => db.destroy(),
  };
}

module.exports = { createDb };
