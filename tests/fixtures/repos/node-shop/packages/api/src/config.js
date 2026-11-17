'use strict';

// Every setting comes from the environment by name; nothing secret lives in the repo.
function readConfig(env = process.env) {
  return {
    port: Number(env.PORT || 3000),
    dbClient: env.DB_CLIENT === 'pg' ? 'pg' : 'sqlite',
    databaseUrl: env.DATABASE_URL || 'shop.sqlite3',
    adminToken: env.ADMIN_API_TOKEN,
    taxRate: Number(env.SALES_TAX_RATE || 0.08),
  };
}

module.exports = { readConfig };
