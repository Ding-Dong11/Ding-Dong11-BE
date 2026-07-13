"""admin_dispositions 에 원천 고유 일련번호(source_seq) 추가

식약처 행정처분(식품판매업) Open API 실제 응답을 확인해보니 DSPSDTLS_SEQ 라는
안정적인 원천 일련번호가 존재한다. 0010에서 만든 복합 자연키
(business_name, disposition_date, type_code, COALESCE(authority,'')) 보다
신뢰도 높은 멱등키이므로 이를 우선 사용한다. 복합 자연키는 원천 일련번호가
없는 경우(CSV 등 다른 소스)를 대비해 그대로 남겨둔다.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admin_dispositions", sa.Column("source_seq", sa.String(50), nullable=True)
    )
    # source_seq 가 없는 행(예: 다른 소스)이 여럿이어도 NULL 은 서로 충돌하지 않으므로
    # 부분 유니크 인덱스로 충분하다.
    op.execute(
        "CREATE UNIQUE INDEX uq_admin_dispositions_source_seq "
        "ON admin_dispositions(source_seq) WHERE source_seq IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_admin_dispositions_source_seq")
    op.drop_column("admin_dispositions", "source_seq")
