"""initial schema

Revision ID: f8a3b2c1
Revises:
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision = "f8a3b2c1"
down_revision = None
branch_labels = None
depends_on = None

jobstatus = postgresql.ENUM(
    "PENDING", "RUNNING", "SUCCESS", "FAILURE",
    name="jobstatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
    jobstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "gps_traces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("storage_uri", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "monitoring_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.Integer(), nullable=False),
        sa.Column("status", jobstatus, nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["trace_id"], ["gps_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pollution_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("pollutant", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["monitoring_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exposure_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.Integer(), nullable=False),
        sa.Column("cumulative_exposure", sa.Float(), nullable=True),
        sa.Column("mean_exposure", sa.Float(), nullable=True),
        sa.Column("peak_exposure", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["trace_id"], ["gps_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exposure_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("location", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("matched_site_id", sa.Integer(), nullable=True),
        sa.Column("matched_concentration", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["matched_site_id"], ["monitoring_sites.id"]),
        sa.ForeignKeyConstraint(["trace_id"], ["gps_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exposure_points")
    op.drop_table("exposure_results")
    op.drop_table("pollution_observations")
    op.drop_table("processing_jobs")
    op.drop_table("monitoring_sites")
    op.drop_table("gps_traces")
    jobstatus.drop(op.get_bind(), checkfirst=True)
