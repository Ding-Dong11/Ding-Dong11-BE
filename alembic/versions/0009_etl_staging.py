"""ETL staging: raw records buffer, run history, geocode cache (공공데이터 적재 파이프라인 보조 테이블)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extract 단계 원본 그대로 보관 → Transform 재실행 시 외부 재호출 없이 재처리 가능.
    # source: 'stores_csv' | 'stores_api' | 'grid_stats' | 'dispositions'
    op.create_table(
        "etl_raw_records",
        sa.Column("raw_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_etl_raw_source_processed", "etl_raw_records", ["source", "processed"])

    # 파이프라인 실행 이력: 재실행 시 마지막 성공 커서에서 재개(incremental)
    op.create_table(
        "etl_run",
        sa.Column("run_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("loaded_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cursor", sa.String(200), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING','SUCCESS','FAILED')", name="ck_etl_run_status"
        ),
    )
    op.create_index("idx_etl_run_source_started", "etl_run", ["source", sa.text("started_at DESC")])

    # 지오코딩 캐시: 동일 주소 재호출 방지 (카카오 1순위 / VWorld fallback)
    op.create_table(
        "raw_geocode_cache",
        sa.Column("cache_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("address_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("address_text", sa.String(300), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("raw_geocode_cache")
    op.drop_table("etl_run")
    op.drop_table("etl_raw_records")
