"""raw 행정처분 레코드 -> admin_dispositions 행.

좌표 확보 우선순위:
1) stores 테이블에서 업체명이 일치하는 상가를 찾아 좌표를 재사용 (지오코딩 호출 절약)
2) 실패 시 주소를 카카오/VWorld 로 지오코딩
3) 그래도 실패하면 좌표 NULL 로 적재 진행 (database.md: 마커만 누락, 적재 자체는 계속)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Engine, select

from app.etl.client.http import EtlHttpClient
from app.etl.geocode.client import geocode_address
from app.etl.schema import stores as stores_table

_FIELD_CANDIDATES: dict[str, list[str]] = {
    # data.go.kr "식품의약품안전처_행정처분결과(식품판매업)" API 실제 응답 필드로 확인됨
    "business_name": ["업소명", "PRCSCITYPOINT_BSSHNM"],
    "type_code": ["행정처분코드"],  # 실 API 에는 별도 코드가 없어 type_name 을 폴백으로 사용
    "type_name": ["행정처분명", "DSPS_TYPECD_NM"],
    "disposition_date": ["행정처분일자", "DSPS_DCSNDT"],
    "violation_content": ["위반내용", "VILTCN"],
    "legal_basis": ["법적근거", "LAWORD_CD_NM"],
    "authority": ["처분청", "DSPS_INSTTCD_NM"],
    "road_address": ["소재지도로명", "ADDR"],
    "jibun_address": ["소재지지번"],
    "source_seq": ["DSPSDTLS_SEQ"],
}


def _pick(raw: dict[str, Any], field_name: str) -> str | None:
    for key in _FIELD_CANDIDATES[field_name]:
        if key in raw and raw[key] not in (None, ""):
            return str(raw[key]).strip()
    return None


def _parse_date(value: str) -> date | None:
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            from datetime import datetime as _dt

            return _dt.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class DispositionRow:
    business_name: str
    type_code: str
    type_name: str
    disposition_date: date
    violation_content: str | None
    legal_basis: str | None
    authority: str | None
    store_id: int | None
    longitude: float | None
    latitude: float | None
    source_seq: str | None


def _match_store_coords(engine: Engine, business_name: str) -> tuple[int, float, float] | None:
    with engine.begin() as conn:
        row = conn.execute(
            select(stores_table.c.store_id, stores_table.c.longitude, stores_table.c.latitude)
            .where(stores_table.c.store_name == business_name)
            .limit(1)
        ).first()
    if row is None:
        return None
    return row.store_id, float(row.longitude), float(row.latitude)


def transform_row(
    raw: dict[str, Any],
    engine: Engine,
    http_client: EtlHttpClient,
    kakao_key: str,
    vworld_key: str,
    geocode_ttl_seconds: int,
) -> DispositionRow | None:
    business_name = _pick(raw, "business_name")
    type_name = _pick(raw, "type_name")
    type_code = _pick(raw, "type_code") or type_name
    date_raw = _pick(raw, "disposition_date")
    source_seq = _pick(raw, "source_seq")

    # source_seq(원천 고유 일련번호) 가 없으면 멱등 upsert 가 불가능하므로 적재 제외.
    if not business_name or not type_code or not date_raw or not source_seq:
        return None

    disposition_date = _parse_date(date_raw)
    if disposition_date is None:
        return None

    store_id: int | None = None
    longitude: float | None = None
    latitude: float | None = None

    matched = _match_store_coords(engine, business_name)
    if matched is not None:
        store_id, longitude, latitude = matched
    else:
        address = _pick(raw, "road_address") or _pick(raw, "jibun_address")
        if address:
            longitude, latitude = geocode_address(
                engine, http_client, address, kakao_key, vworld_key, geocode_ttl_seconds
            )

    return DispositionRow(
        business_name=business_name,
        type_code=type_code,
        type_name=type_name or type_code,
        disposition_date=disposition_date,
        violation_content=_pick(raw, "violation_content"),
        legal_basis=_pick(raw, "legal_basis"),
        authority=_pick(raw, "authority"),
        store_id=store_id,
        longitude=longitude,
        latitude=latitude,
        source_seq=source_seq,
    )
