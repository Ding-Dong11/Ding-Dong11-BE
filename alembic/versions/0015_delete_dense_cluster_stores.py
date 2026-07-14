"""동일 좌표 50개 이상 밀집 상가(대형 건물/쇼핑몰) 삭제

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-15

삭제 기준:
- 동일 (longitude, latitude) 좌표에 50개 이상 상가가 집중된 클러스터
- 단, road_address 또는 store_name에 전통시장 키워드('시장', '오일장')가 포함된
  좌표는 소상공인 전통시장으로 판단하여 보존

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

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 삭제 대상 store_id CTE
# 1) dense: 50개 이상 클러스터 좌표
# 2) market_coords: 전통시장 키워드 포함 좌표 (보존 대상)
# 3) 최종: dense에 속하면서 market_coords에 없는 상가
_TARGET_CTE = """
    WITH dense AS (
        SELECT longitude, latitude
        FROM stores
        GROUP BY longitude, latitude
        HAVING COUNT(*) >= 50
    ),
    market_coords AS (
        SELECT DISTINCT s.longitude, s.latitude
        FROM stores s
        JOIN dense d ON s.longitude = d.longitude AND s.latitude = d.latitude
        WHERE s.road_address LIKE '%시장%'
           OR s.road_address LIKE '%오일장%'
           OR s.store_name   LIKE '%시장%'
           OR s.store_name   LIKE '%오일장%'
    ),
    target_ids AS (
        SELECT st.store_id
        FROM stores st
        JOIN dense d ON st.longitude = d.longitude AND st.latitude = d.latitude
        LEFT JOIN market_coords m ON m.longitude = st.longitude AND m.latitude = st.latitude
        WHERE m.longitude IS NULL
    )
"""


def upgrade() -> None:
    # 1) reward_verifications: 삭제 대상 stores 의 QR 코드를 참조하는 인증 이력 삭제
    op.execute(f"""
        {_TARGET_CTE}
        DELETE FROM reward_verifications
        WHERE qr_id IN (
            SELECT sqc.qr_id
            FROM store_qr_codes sqc
            JOIN target_ids t ON t.store_id = sqc.store_id
        )
    """)

    # 2) store_qr_codes: 삭제 대상 stores 에 속한 QR 코드 삭제
    op.execute(f"""
        {_TARGET_CTE}
        DELETE FROM store_qr_codes
        WHERE store_id IN (SELECT store_id FROM target_ids)
    """)

    # 3) admin_dispositions.store_id → NULL (nullable FK, 처분 이력은 보존)
    op.execute(f"""
        {_TARGET_CTE}
        UPDATE admin_dispositions
        SET store_id = NULL
        WHERE store_id IN (SELECT store_id FROM target_ids)
    """)

    # 4) sale_stores.store_id → NULL (nullable FK, 세일 매장 데이터는 보존)
    op.execute(f"""
        {_TARGET_CTE}
        UPDATE sale_stores
        SET store_id = NULL
        WHERE store_id IN (SELECT store_id FROM target_ids)
    """)

    # 5) stores 삭제
    op.execute(f"""
        {_TARGET_CTE}
        DELETE FROM stores
        WHERE store_id IN (SELECT store_id FROM target_ids)
    """)


def downgrade() -> None:
    raise NotImplementedError(
        "밀집 클러스터 stores 대량 삭제는 되돌릴 수 없습니다. "
        "원천 데이터에서 ETL 재실행으로 복구하세요."
    )
