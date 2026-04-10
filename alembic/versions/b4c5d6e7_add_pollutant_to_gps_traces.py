"""add pollutant to gps_traces

Revision ID: b4c5d6e7
Revises: f8a3b2c1
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

revision = "b4c5d6e7"
down_revision = "f8a3b2c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gps_traces",
        sa.Column("pollutant", sa.String(length=64), nullable=False, server_default="PM2.5"),
    )


def downgrade() -> None:
    op.drop_column("gps_traces", "pollutant")
