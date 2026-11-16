'use strict';

const { createApp } = require('./app');
const { readConfig } = require('./config');
const { createDb } = require('./db');

const config = readConfig();
const db = createDb(config);
const server = createApp({ db, config }).listen(config.port, () => {
  console.log(`api listening on :${config.port}`);
});

process.on('SIGTERM', () => server.close(() => db.close()));
