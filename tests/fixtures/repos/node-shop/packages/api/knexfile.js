'use strict';

// Loaded by the knex CLI (`npm run migrate`) on its own, so it only reads the environment.
const client = process.env.DB_CLIENT === 'pg' ? 'pg' : 'better-sqlite3';
const filename = process.env.DATABASE_URL || 'shop.sqlite3';

module.exports = {
  client,
  connection: client === 'pg' ? process.env.DATABASE_URL : { filename },
  useNullAsDefault: client !== 'pg',
  migrations: { directory: './migrations' },
};
