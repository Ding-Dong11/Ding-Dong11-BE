"""admin_dispositions 복합 자연키 제거 (실제 데이터로 반증됨)

실제 식약처 행정처분 API 데이터를 적재해보니, 동일한
(business_name, disposition_date, type_code, authority) 조합인데 서로 다른
source_seq(원천 고유 일련번호)를 가진 별개의 처분 건이 존재했다. 즉 0010의
전제("이 네 컬럼 조합이 유일하다")가 실제로는 거짓이었다. 0011에서 도입한
source_seq 가 유일하게 신뢰 가능한 멱등키이므로, 잘못된 전제의 자연키 제약을
제거한다.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_admin_dispositions_natural")


def downgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_admin_dispositions_natural
        ON admin_dispositions (business_name, disposition_date, type_code, COALESCE(authority, ''))
        """
    )
