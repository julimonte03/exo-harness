# Node Shop

Storefront and order API for a small merchandise shop, as an npm workspaces monorepo:
`packages/api` (Express, knex on SQLite or Postgres), `packages/web` (React + Vite)
and `packages/shared` (prices, limits and types used by both).

Run `npm install`, then `npm run migrate -w @shop/api`, `npm run seed -w @shop/api`,
`npm start -w @shop/api` and `npm run dev -w @shop/web`. The API reads its settings
from the environment: `PORT`, `DB_CLIENT` (`sqlite` or `pg`), `DATABASE_URL`,
`SALES_TAX_RATE` and `ADMIN_API_TOKEN` for the back office.
