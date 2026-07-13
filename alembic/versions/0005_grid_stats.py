"""grid_stats / grid_stat_metrics / grid_stat_values (국토지리정보원 격자 통계)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grid_stats",
        sa.Column("grid_id", sa.String(30), primary_key=True),
        # UTM-K(EPSG:5179) → WGS84(EPSG:4326) 변환 후 적재 (database.md)
        sa.Column("center_longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("center_latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("min_x", sa.Numeric(10, 7), nullable=False),
        sa.Column("min_y", sa.Numeric(10, 7), nullable=False),
        sa.Column("max_x", sa.Numeric(10, 7), nullable=False),
        sa.Column("max_y", sa.Numeric(10, 7), nullable=False),
    )

    op.create_table(
        "grid_stat_metrics",
        sa.Column("metric_code", sa.String(30), primary_key=True),
        sa.Column("metric_name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(30), nullable=True),
    )

    op.create_table(
        "grid_stat_values",
        sa.Column("value_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("grid_id", sa.String(30), sa.ForeignKey("grid_stats.grid_id"), nullable=False),
        sa.Column("metric_code", sa.String(30), sa.ForeignKey("grid_stat_metrics.metric_code"), nullable=False),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
    )
    op.create_index("idx_grid_stat_values_grid", "grid_stat_values", ["grid_id"])
    op.create_index("idx_grid_stat_values_metric", "grid_stat_values", ["metric_code"])
    op.create_unique_constraint(
        "uq_grid_stat_values_grid_metric", "grid_stat_values", ["grid_id", "metric_code"]
    )


def downgrade() -> None:
    op.drop_table("grid_stat_values")
    op.drop_table("grid_stat_metrics")
    op.drop_table("grid_stats")
