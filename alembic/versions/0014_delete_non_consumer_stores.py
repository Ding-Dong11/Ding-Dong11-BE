"""일반 소비자 소비 불가 업종(제조·건설·도매·B2B 서비스 등) stores 데이터 정리

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-14

삭제 대상: app.etl.sources.stores.excluded_industries 에 정의된 제외 산업 코드를
가진 stores 레코드 및 연관 데이터.

FK 삭제 순서 (참조 무결성):
  1. reward_verifications (store_qr_codes 복합 FK)
  2. store_qr_codes (stores FK, NOT NULL)
  3. admin_dispositions.store_id → NULL  (nullable FK)
  4. sale_stores.store_id → NULL         (nullable FK)
  5. stores 삭제
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from app.etl.sources.stores.excluded_industries import EXCLUDED_CODES, EXCLUDED_PREFIXES

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _build_where() -> str:
    """excluded_industries 상수에서 SQL WHERE 절 생성."""
    prefix_clauses = [f"industry_code LIKE '{p}%'" for p in sorted(EXCLUDED_PREFIXES)]
    code_list = ", ".join(f"'{c}'" for c in sorted(EXCLUDED_CODES))
    code_clause = f"industry_code IN ({code_list})"
    all_clauses = prefix_clauses + [code_clause]
    return "(\n        " + "\n        OR ".join(all_clauses) + "\n    )"


def upgrade() -> None:
    where = _build_where()

    # 1) reward_verifications: 삭제 대상 stores 의 QR 코드를 참조하는 인증 이력 삭제
    op.execute(f"""
        DELETE FROM reward_verifications
        WHERE qr_id IN (
            SELECT sqc.qr_id
            FROM store_qr_codes sqc
            JOIN stores s ON s.store_id = sqc.store_id
            WHERE {where}
        )
    """)

    # 2) store_qr_codes: 삭제 대상 stores 에 속한 QR 코드 삭제
    op.execute(f"""
        DELETE FROM store_qr_codes
        WHERE store_id IN (
            SELECT store_id FROM stores WHERE {where}
        )
    """)

    # 3) admin_dispositions.store_id → NULL (nullable FK, 처분 이력은 보존)
    op.execute(f"""
        UPDATE admin_dispositions
        SET store_id = NULL
        WHERE store_id IN (
            SELECT store_id FROM stores WHERE {where}
        )
    """)

    # 4) sale_stores.store_id → NULL (nullable FK, 세일 매장 데이터는 보존)
    op.execute(f"""
        UPDATE sale_stores
        SET store_id = NULL
        WHERE store_id IN (
            SELECT store_id FROM stores WHERE {where}
        )
    """)

    # 5) stores 삭제
    op.execute(f"""
        DELETE FROM stores WHERE {where}
    """)


def downgrade() -> None:
    # 원천 데이터(공공데이터 CSV/API)에서 재적재해야 하므로 downgrade 미지원
    raise NotImplementedError(
        "stores 대량 삭제는 되돌릴 수 없습니다. "
        "원천 데이터에서 ETL 재실행으로 복구하세요."
    )
