"""stores table (소상공인시장진흥공단 상가업소) + geom/search_tsv generated columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("store_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("store_number", sa.String(50), nullable=False, unique=True),
        sa.Column("store_name", sa.String(200), nullable=False),
        sa.Column("branch_name", sa.String(200), nullable=True),
        sa.Column("small_code", sa.String(10), sa.ForeignKey("category_small.small_code"), nullable=True),
        sa.Column("adong_code", sa.String(10), sa.ForeignKey("adong.adong_code"), nullable=True),
        sa.Column("bdong_code", sa.String(10), sa.ForeignKey("bdong.bdong_code"), nullable=True),
        sa.Column("industry_code", sa.String(20), sa.ForeignKey("standard_industry.industry_code"), nullable=True),
        sa.Column("road_address", sa.String(300), nullable=True),
        sa.Column("jibun_address", sa.String(300), nullable=True),
        # database.md: 지도 대상 → 적재 시 NOT NULL 권장
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
    )
    op.create_index("idx_stores_small_code", "stores", ["small_code"])
    op.create_index("idx_stores_adong_code", "stores", ["adong_code"])
    op.create_index("idx_stores_bdong_code", "stores", ["bdong_code"])
    op.create_index("idx_stores_industry_code", "stores", ["industry_code"])

    # 공간 인덱스: PostGIS geometry 생성 컬럼 + GiST (develop.md/database.md)
    op.execute(
        """
        ALTER TABLE stores ADD COLUMN geom geometry(Point, 4326)
          GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude::float8, latitude::float8), 4326)) STORED
        """
    )
    op.execute("CREATE INDEX idx_stores_geom ON stores USING GIST (geom)")

    # 전문검색: tsvector 생성 컬럼 + GIN (develop.md)
    op.execute(
        """
        ALTER TABLE stores ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(store_name,'') || ' ' || coalesce(branch_name,''))
          ) STORED
        """
    )
    op.execute("CREATE INDEX idx_stores_search ON stores USING GIN (search_tsv)")


def downgrade() -> None:
    op.drop_table("stores")
