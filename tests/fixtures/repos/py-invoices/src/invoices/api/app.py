"""Application factory."""

from __future__ import annotations

from fastapi import FastAPI

from invoices.core.config import Settings, load_settings
from invoices.storage.repositories import make_session_factory

from . import routes_auth, routes_customers, routes_invoices, routes_payments
from .errors import register_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Invoices API")
    app.state.settings = settings
    app.state.session_factory = make_session_factory(settings)
    for module in (routes_auth, routes_customers, routes_invoices, routes_payments):
        app.include_router(module.router)
    register_error_handlers(app)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
