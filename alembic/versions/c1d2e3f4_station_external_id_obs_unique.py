"""monitoring site external id + unique observations

Revision ID: c1d2e3f4
Revises: b4c5d6e7
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4"
down_revision = "b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitoring_sites",
        sa.Column("external_station_id", sa.String(length=64), nullable=True),
    )
    # PostgreSQL UNIQUE allows multiple NULLs (rows without external_station_id).
    op.create_index(
        "ix_monitoring_sites_external_station_id",
        "monitoring_sites",
        ["external_station_id"],
        unique=True,
    )
    op.create_unique_constraint(
        "uq_pollution_obs_site_time_pollutant",
        "pollution_observations",
        ["site_id", "timestamp", "pollutant"],
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_monitoring_sites_location_gist "
            "ON monitoring_sites USING GIST (location)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_monitoring_sites_location_gist"))
    op.drop_constraint("uq_pollution_obs_site_time_pollutant", "pollution_observations", type_="unique")
    op.drop_index("ix_monitoring_sites_external_station_id", table_name="monitoring_sites")
    op.drop_column("monitoring_sites", "external_station_id")
