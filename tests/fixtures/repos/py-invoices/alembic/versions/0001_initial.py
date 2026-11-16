"""initial schema: customers, invoices and payments

Revision ID: 0001
Revises:
Create Date: 2026-03-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def money(name: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(12, 2), nullable=False)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("tax_region", sa.String(8), nullable=False),
        money("credit_limit"),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("number", sa.String(32), nullable=False, unique=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("lines", sa.JSON, nullable=False),
        *(money(name) for name in ("subtotal", "discount", "tax", "total")),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("invoice_id", sa.Integer, sa.ForeignKey("invoices.id"), nullable=False),
        money("amount"),
        money("refunded"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("card_last4", sa.String(4), nullable=False),  # never the full number
    )


def downgrade() -> None:
    for table in ("payments", "invoices", "customers"):
        op.drop_table(table)
