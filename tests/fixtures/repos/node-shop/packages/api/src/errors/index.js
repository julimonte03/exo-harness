'use strict';

/** An error whose status and message are safe to send to the client. */
class HttpError extends Error {
  constructor(status, message, details) {
    super(message);
    Object.assign(this, { name: 'HttpError', status, details });
  }
}

module.exports = { HttpError };
