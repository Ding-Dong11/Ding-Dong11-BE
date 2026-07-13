"""admin_dispositions table (식약처 행정처분) + geom/search_tsv generated columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_dispositions",
        sa.Column("disposition_id", sa.BigInteger, sa.Identity(), primary_key=True),
        # 식약처 원천이라 stores 매칭 성공 시에만 채움 (database.md)
        sa.Column("store_id", sa.BigInteger, sa.ForeignKey("stores.store_id"), nullable=True),
        sa.Column("business_name", sa.String(200), nullable=False),
        sa.Column("type_code", sa.String(20), sa.ForeignKey("disposition_types.type_code"), nullable=False),
        sa.Column("disposition_date", sa.Date, nullable=False),
        sa.Column("violation_content", sa.Text, nullable=True),
        sa.Column("legal_basis", sa.String(300), nullable=True),
        sa.Column("authority", sa.String(200), nullable=True),
        sa.Column("small_code", sa.String(10), sa.ForeignKey("category_small.small_code"), nullable=True),
        sa.Column("adong_code", sa.String(10), sa.ForeignKey("adong.adong_code"), nullable=True),
        # 좌표는 지오코딩 실패 시 NULL 허용 (database.md ETL 설계)
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
    )
    op.create_index("idx_dispositions_store", "admin_dispositions", ["store_id"])
    op.create_index("idx_dispositions_type", "admin_dispositions", ["type_code"])
    op.create_index("idx_dispositions_small_code", "admin_dispositions", ["small_code"])
    op.create_index("idx_dispositions_adong", "admin_dispositions", ["adong_code"])
    op.create_index("idx_dispositions_date", "admin_dispositions", ["disposition_date"])

    op.execute(
        """
        ALTER TABLE admin_dispositions ADD COLUMN geom geometry(Point, 4326)
          GENERATED ALWAYS AS (
            CASE WHEN longitude IS NOT NULL AND latitude IS NOT NULL
                 THEN ST_SetSRID(ST_MakePoint(longitude::float8, latitude::float8), 4326)
            END
          ) STORED
        """
    )
    op.execute("CREATE INDEX idx_dispositions_geom ON admin_dispositions USING GIST (geom)")

    op.execute(
        """
        ALTER TABLE admin_dispositions ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (to_tsvector('simple', coalesce(business_name,''))) STORED
        """
    )
    op.execute("CREATE INDEX idx_dispositions_search ON admin_dispositions USING GIN (search_tsv)")


def downgrade() -> None:
    op.drop_table("admin_dispositions")
