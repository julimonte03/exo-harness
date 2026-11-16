FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 INVOICES_SANDBOX=false
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY alembic ./alembic
RUN pip install --no-cache-dir .

# INVOICES_SIGNING_KEY and INVOICES_DATABASE_URL are injected at run time, never baked in.
USER nobody
EXPOSE 8000
CMD ["uvicorn", "invoices.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
