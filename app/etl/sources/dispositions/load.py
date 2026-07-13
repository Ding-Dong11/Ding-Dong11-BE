from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.etl.base import LoadResult
from app.etl.schema import admin_dispositions, disposition_types
from app.etl.sources.dispositions.transform import DispositionRow


def upsert_disposition_types(engine: Engine, rows: list[DispositionRow]) -> None:
    types = {r.type_code: r.type_name for r in rows}
    if not types:
        return
    stmt = pg_insert(disposition_types).values(
        [{"type_code": k, "type_name": v} for k, v in types.items()]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[disposition_types.c.type_code],
        set_={"type_name": stmt.excluded.type_name},
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def _row_values(r: DispositionRow) -> dict:
    return {
        "store_id": r.store_id,
        "business_name": r.business_name,
        "type_code": r.type_code,
        "disposition_date": r.disposition_date,
        "violation_content": r.violation_content,
        "legal_basis": r.legal_basis,
        "authority": r.authority,
        "longitude": r.longitude,
        "latitude": r.latitude,
        "source_seq": r.source_seq,
    }


def upsert_dispositions(engine: Engine, rows: list[DispositionRow]) -> LoadResult:
    """source_seq(원천 고유 일련번호) 를 멱등키로 사용해 upsert.

    실제 데이터 검증 결과 (business_name, disposition_date, type_code, authority) 는
    유일하지 않다 — 같은 조합인데 서로 다른 별개의 처분 건(다른 source_seq)이 존재한다.
    따라서 자연키 폴백은 두지 않는다: source_seq 가 없는 행은 transform 단계에서 이미
    걸러진다(app/etl/sources/dispositions/transform.py).
    """
    if not rows:
        return LoadResult()

    # data.go.kr 페이징 중 동일 레코드가 두 페이지에 걸쳐 중복 반환되는 경우가 있어,
    # 한 INSERT 문 안에서 source_seq 가 중복되면 안 된다(Postgres 는 ON CONFLICT DO
    # UPDATE 가 같은 배치 내 동일 충돌키를 두 번 처리하지 못함) — 배치 내 중복 제거.
    deduped: dict[str, DispositionRow] = {r.source_seq: r for r in rows}
    rows = list(deduped.values())

    stmt = pg_insert(admin_dispositions).values([_row_values(r) for r in rows])
    stmt = stmt.on_conflict_do_update(
        index_elements=[admin_dispositions.c.source_seq],
        index_where=admin_dispositions.c.source_seq.isnot(None),
        set_={
            "store_id": stmt.excluded.store_id,
            "business_name": stmt.excluded.business_name,
            "type_code": stmt.excluded.type_code,
            "disposition_date": stmt.excluded.disposition_date,
            "violation_content": stmt.excluded.violation_content,
            "legal_basis": stmt.excluded.legal_basis,
            "authority": stmt.excluded.authority,
            "longitude": stmt.excluded.longitude,
            "latitude": stmt.excluded.latitude,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)

    return LoadResult(inserted=len(rows))
