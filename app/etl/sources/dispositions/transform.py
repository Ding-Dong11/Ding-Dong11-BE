"""raw 행정처분 레코드 -> admin_dispositions 행.

좌표 확보 + store_id 매칭 우선순위:
1) 주소 지오코딩으로 기준 좌표 확보
2) 업체명 완전 일치 후보 중 기준 좌표에서 500m 이내인 상가 선택
   - 후보가 1건: 거리 검증 통과 시 매칭
   - 후보가 여러 건: 가장 가까운 것 선택 (500m 이내)
3) 지오코딩 실패 + 업체명 단독 1건 일치: 위치 검증 없이 매칭
4) 모두 실패하면 store_id = null, 좌표는 지오코딩 결과 그대로
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Engine, select

from app.etl.client.http import EtlHttpClient
from app.etl.geocode.client import geocode_address
from app.etl.schema import stores as stores_table

_MATCH_RADIUS_M = 500  # 매칭 허용 거리 (미터)

_FIELD_CANDIDATES: dict[str, list[str]] = {
    "business_name": ["업소명", "PRCSCITYPOINT_BSSHNM"],
    "type_code": ["행정처분코드"],
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


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """두 WGS84 좌표 사이 거리(미터) — Haversine 공식."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


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


def _find_matching_store(
    engine: Engine,
    business_name: str,
    ref_lon: float | None,
    ref_lat: float | None,
) -> tuple[int, float, float] | None:
    """업체명 일치 후보 중 기준 좌표(ref_lon, ref_lat)와 가장 가까운 상가 반환.

    - ref 좌표가 있으면 _MATCH_RADIUS_M 이내인 후보만 허용
    - ref 좌표가 없으면 후보가 1건일 때만 반환 (위치 검증 불가)
    """
    with engine.begin() as conn:
        rows = conn.execute(
            select(
                stores_table.c.store_id,
                stores_table.c.longitude,
                stores_table.c.latitude,
            ).where(stores_table.c.store_name == business_name)
        ).fetchall()

    if not rows:
        return None

    if ref_lon is not None and ref_lat is not None:
        candidates = [
            (r, _haversine_m(float(r.longitude), float(r.latitude), ref_lon, ref_lat))
            for r in rows
        ]
        within = [(r, d) for r, d in candidates if d <= _MATCH_RADIUS_M]
        if not within:
            return None
        best, _ = min(within, key=lambda x: x[1])
        return best.store_id, float(best.longitude), float(best.latitude)

    # 지오코딩 실패: 업체명 단독 1건 일치만 안전하게 허용
    if len(rows) == 1:
        r = rows[0]
        return r.store_id, float(r.longitude), float(r.latitude)

    return None


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

    if not business_name or not type_code or not date_raw or not source_seq:
        return None

    disposition_date = _parse_date(date_raw)
    if disposition_date is None:
        return None

    # 1) 주소 지오코딩 먼저 — 기준 좌표 확보
    address = _pick(raw, "road_address") or _pick(raw, "jibun_address")
    geo_lon: float | None = None
    geo_lat: float | None = None
    if address:
        geo_lon, geo_lat = geocode_address(
            engine, http_client, address, kakao_key, vworld_key, geocode_ttl_seconds
        )

    # 2) 업체명 + 기준 좌표로 stores 매칭
    matched = _find_matching_store(engine, business_name, geo_lon, geo_lat)

    store_id: int | None = None
    longitude: float | None = None
    latitude: float | None = None

    if matched is not None:
        store_id, longitude, latitude = matched
    elif geo_lon is not None:
        # 매칭 실패해도 지오코딩 좌표는 마커 표시에 사용
        longitude, latitude = geo_lon, geo_lat

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
