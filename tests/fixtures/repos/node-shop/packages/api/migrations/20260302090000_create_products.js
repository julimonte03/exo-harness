'use strict';

exports.up = (knex) =>
  knex.schema.createTable('products', (table) => {
    table.string('id').primary();
    table.string('name').notNullable();
    table.integer('price_cents').notNullable();
    table.integer('on_hand').notNullable().defaultTo(0);
    table.timestamps(true, true);
  });

exports.down = (knex) => knex.schema.dropTable('products');
