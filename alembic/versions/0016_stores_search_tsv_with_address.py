"""stores.search_tsv: road_address 포함으로 재빌드

store_name + branch_name 만 커버하던 search_tsv 생성 컬럼을
road_address 까지 포함하도록 DROP → ADD 방식으로 재생성.
idx_stores_search GIN 인덱스도 함께 재생성.

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-15
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_stores_search")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS search_tsv")
    op.execute(
        """
        ALTER TABLE stores ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (
            to_tsvector('simple',
              coalesce(store_name, '')  || ' ' ||
              coalesce(branch_name, '') || ' ' ||
              coalesce(road_address, '')
            )
          ) STORED
        """
    )
    op.execute("CREATE INDEX idx_stores_search ON stores USING GIN (search_tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_stores_search")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS search_tsv")
    op.execute(
        """
        ALTER TABLE stores ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (
            to_tsvector('simple',
              coalesce(store_name, '') || ' ' || coalesce(branch_name, '')
            )
          ) STORED
        """
    )
    op.execute("CREATE INDEX idx_stores_search ON stores USING GIN (search_tsv)")
