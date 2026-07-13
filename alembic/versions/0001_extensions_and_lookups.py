"""extensions and lookup tables (sido/sigungu/adong/bdong, category, standard_industry, disposition_types)

Revision ID: 0001
Revises:
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS: 지도 좌표 공간 타입/인덱스 (database.md)
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── 행정구역 ──
    op.create_table(
        "sido",
        sa.Column("sido_code", sa.String(10), primary_key=True),
        sa.Column("sido_name", sa.String(100), nullable=False),
    )

    op.create_table(
        "sigungu",
        sa.Column("sigungu_code", sa.String(10), primary_key=True),
        sa.Column("sido_code", sa.String(10), sa.ForeignKey("sido.sido_code"), nullable=False),
        sa.Column("sigungu_name", sa.String(100), nullable=False),
    )
    op.create_index("idx_sigungu_sido", "sigungu", ["sido_code"])

    op.create_table(
        "adong",
        sa.Column("adong_code", sa.String(10), primary_key=True),
        sa.Column("sigungu_code", sa.String(10), sa.ForeignKey("sigungu.sigungu_code"), nullable=False),
        sa.Column("adong_name", sa.String(100), nullable=False),
    )
    op.create_index("idx_adong_sigungu", "adong", ["sigungu_code"])

    op.create_table(
        "bdong",
        sa.Column("bdong_code", sa.String(10), primary_key=True),
        sa.Column("sigungu_code", sa.String(10), sa.ForeignKey("sigungu.sigungu_code"), nullable=False),
        sa.Column("bdong_name", sa.String(100), nullable=False),
    )
    op.create_index("idx_bdong_sigungu", "bdong", ["sigungu_code"])

    # ── 업종 분류 (대/중/소) ──
    op.create_table(
        "category_large",
        sa.Column("large_code", sa.String(10), primary_key=True),
        sa.Column("large_name", sa.String(100), nullable=False),
    )

    op.create_table(
        "category_middle",
        sa.Column("middle_code", sa.String(10), primary_key=True),
        sa.Column("large_code", sa.String(10), sa.ForeignKey("category_large.large_code"), nullable=False),
        sa.Column("middle_name", sa.String(100), nullable=False),
    )
    op.create_index("idx_category_middle_large", "category_middle", ["large_code"])

    op.create_table(
        "category_small",
        sa.Column("small_code", sa.String(10), primary_key=True),
        sa.Column("middle_code", sa.String(10), sa.ForeignKey("category_middle.middle_code"), nullable=False),
        sa.Column("small_name", sa.String(100), nullable=False),
    )
    op.create_index("idx_category_small_middle", "category_small", ["middle_code"])

    # ── 표준산업분류 룩업 ──
    op.create_table(
        "standard_industry",
        sa.Column("industry_code", sa.String(20), primary_key=True),
        sa.Column("industry_name", sa.String(200), nullable=False),
    )

    # ── 행정처분 유형 룩업 ──
    op.create_table(
        "disposition_types",
        sa.Column("type_code", sa.String(20), primary_key=True),
        sa.Column("type_name", sa.String(200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("disposition_types")
    op.drop_table("standard_industry")
    op.drop_index("idx_category_small_middle", table_name="category_small")
    op.drop_table("category_small")
    op.drop_index("idx_category_middle_large", table_name="category_middle")
    op.drop_table("category_middle")
    op.drop_table("category_large")
    op.drop_index("idx_bdong_sigungu", table_name="bdong")
    op.drop_table("bdong")
    op.drop_index("idx_adong_sigungu", table_name="adong")
    op.drop_table("adong")
    op.drop_index("idx_sigungu_sido", table_name="sigungu")
    op.drop_table("sigungu")
    op.drop_table("sido")
    # postgis 확장은 다른 DB 객체가 의존할 수 있어 downgrade 에서 자동 제거하지 않음
