'use strict';

// Postgres keeps lines and totals in json columns, so rows pass through untouched.
module.exports = {
  connectionOptions: (url) => ({ client: 'pg', connection: url, useNullAsDefault: false }),
  serialize: (row) => row,
  deserialize: (row) => row,
};
