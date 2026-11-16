# py-invoices

Invoicing API: customers, invoices with taxes and discounts, card payments and
reconciliation. FastAPI, pydantic and SQLAlchemy, with Alembic migrations; the
contract is in `openapi.yaml`. Run it with `alembic upgrade head && invoices serve`.

`INVOICES_SIGNING_KEY` (32+ characters) comes from your secret store; `.env.example`
lists the rest. The sandbox only accepts published test cards (`4111 1111 1111 1111`).
