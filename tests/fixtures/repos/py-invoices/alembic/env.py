"""Alembic environment: runs the migrations against the configured database."""

from alembic import context
from sqlalchemy import create_engine, pool

from invoices.core.config import load_settings
from invoices.storage.models import Base

engine = create_engine(load_settings().database_url, poolclass=pool.NullPool)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
