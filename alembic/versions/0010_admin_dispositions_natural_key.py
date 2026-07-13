"""admin_dispositions natural unique key (ETL 멱등 upsert용)

식약처 원천 데이터에는 안정적인 대리키가 없어, 재적재 시 중복 없이
upsert 하려면 (업체명, 처분일자, 처분유형, 처분기관) 조합을 자연키로 사용한다.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-13
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # authority 는 nullable 이라 일반 UNIQUE 제약은 NULL 을 서로 다른 값으로 취급해
    # 멱등 upsert가 깨진다 (동일 업체·일자·유형인데 authority=NULL 인 행이 중복 삽입됨).
    # COALESCE 로 NULL 을 고정값으로 치환한 표현식 유니크 인덱스로 대체.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_admin_dispositions_natural
        ON admin_dispositions (business_name, disposition_date, type_code, COALESCE(authority, ''))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_admin_dispositions_natural")
