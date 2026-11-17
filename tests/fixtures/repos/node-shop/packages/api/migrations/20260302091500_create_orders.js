'use strict';

const { ORDER_STATUSES } = require('../src/orders/status');

exports.up = (knex) =>
  knex.schema.createTable('orders', (table) => {
    table.uuid('id').primary();
    table.string('email').notNullable();
    table.enu('status', ORDER_STATUSES).notNullable().defaultTo('pending');
    table.json('lines').notNullable();
    table.json('totals').notNullable();
    table.boolean('refund_required').notNullable().defaultTo(false);
    table.timestamps(true, true);
    table.index(['status']);
  });

exports.down = (knex) => knex.schema.dropTable('orders');
