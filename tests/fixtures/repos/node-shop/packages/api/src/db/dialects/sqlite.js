'use strict';

const parse = (row) => row && { ...row, lines: JSON.parse(row.lines), totals: JSON.parse(row.totals) };

// SQLite has no json type: lines and totals are stored as text.
module.exports = {
  connectionOptions: (filename) => ({ client: 'better-sqlite3', connection: { filename } }),
  serialize: (row) => ({
    ...row,
    ...(row.lines && { lines: JSON.stringify(row.lines) }),
    ...(row.totals && { totals: JSON.stringify(row.totals) }),
  }),
  deserialize: parse,
};
