"""raw 상가 레코드(CSV/API) -> stores 테이블 행 + 지역/업종 룩업 행."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# CSV(한글 헤더)와 API(영문 필드) 양쪽에서 값을 찾기 위한 후보 키 목록.
_FIELD_CANDIDATES: dict[str, list[str]] = {
    "store_number": ["상가업소번호", "bizesId"],
    "store_name": ["상호명", "bizesNm"],
    "branch_name": ["지점명", "brchNm"],
    "small_code": ["상권업종소분류코드", "indsSclsCd"],
    "small_name": ["상권업종소분류명", "indsSclsNm"],
    "middle_code": ["상권업종중분류코드", "indsMclsCd"],
    "middle_name": ["상권업종중분류명", "indsMclsNm"],
    "large_code": ["상권업종대분류코드", "indsLclsCd"],
    "large_name": ["상권업종대분류명", "indsLclsNm"],
    "industry_code": ["표준산업분류코드", "ksicCd"],
    "industry_name": ["표준산업분류명", "ksicNm"],
    "adong_code": ["행정동코드", "adongCd"],
    "adong_name": ["행정동명", "adongNm"],
    "bdong_code": ["법정동코드", "ldongCd"],
    "bdong_name": ["법정동명", "ldongNm"],
    "sigungu_code": ["시군구코드", "sigunguCd"],
    "sigungu_name": ["시군구명", "sigunguNm"],
    "sido_code": ["시도코드", "ctprvnCd"],
    "sido_name": ["시도명", "ctprvnNm"],
    "road_address": ["도로명주소", "rdnmAdr"],
    "jibun_address": ["지번주소", "lnoAdr"],
    "longitude": ["경도", "lon"],
    "latitude": ["위도", "lat"],
}


def _pick(raw: dict[str, Any], field_name: str) -> str | None:
    for key in _FIELD_CANDIDATES[field_name]:
        if key in raw and raw[key] not in (None, ""):
            return str(raw[key]).strip()
    return None


@dataclass
class StoreRow:
    store_number: str
    store_name: str
    branch_name: str | None
    small_code: str | None
    adong_code: str | None
    bdong_code: str | None
    industry_code: str | None
    road_address: str | None
    jibun_address: str | None
    longitude: float
    latitude: float


@dataclass
class LookupRows:
    sido: dict[str, str] = field(default_factory=dict)
    sigungu: dict[str, tuple[str, str]] = field(default_factory=dict)  # code -> (sido_code, name)
    adong: dict[str, tuple[str, str]] = field(default_factory=dict)  # code -> (sigungu_code, name)
    bdong: dict[str, tuple[str, str]] = field(default_factory=dict)
    category_large: dict[str, str] = field(default_factory=dict)
    category_middle: dict[str, tuple[str, str]] = field(default_factory=dict)
    category_small: dict[str, tuple[str, str]] = field(default_factory=dict)
    standard_industry: dict[str, str] = field(default_factory=dict)


def transform_row(raw: dict[str, Any], lookups: LookupRows) -> StoreRow | None:
    store_number = _pick(raw, "store_number")
    store_name = _pick(raw, "store_name")
    longitude = _pick(raw, "longitude")
    latitude = _pick(raw, "latitude")

    # database.md: 지도 대상이라 좌표 결측 시 적재 제외
    if not store_number or not store_name or not longitude or not latitude:
        return None

    small_code = _pick(raw, "small_code")
    adong_code = _pick(raw, "adong_code")
    bdong_code = _pick(raw, "bdong_code")
    industry_code = _pick(raw, "industry_code")
    sido_code = _pick(raw, "sido_code")
    sigungu_code = _pick(raw, "sigungu_code")

    # 공공데이터 특성상 코드는 있는데 명칭이 비어있는 행이 실제로 존재한다
    # (예: 법정동코드는 있지만 법정동명이 빈 값). 이름이 없으면 코드를 이름 대신
    # 써서라도 룩업 행을 만들어 FK 무결성을 지킨다. 상위 코드(부모)가 아예 없으면
    # 룩업 자체를 만들 수 없으므로, 그 경우엔 stores 쪽 참조도 함께 비운다
    # (FK 위반으로 적재 전체가 실패하는 것을 방지).
    if sido_code and (name := _pick(raw, "sido_name")):
        lookups.sido[sido_code] = name
    elif sido_code:
        lookups.sido[sido_code] = sido_code

    if sigungu_code and sido_code:
        lookups.sigungu[sigungu_code] = (sido_code, _pick(raw, "sigungu_name") or sigungu_code)
    else:
        sigungu_code = None

    if adong_code and sigungu_code:
        lookups.adong[adong_code] = (sigungu_code, _pick(raw, "adong_name") or adong_code)
    else:
        adong_code = None

    if bdong_code and sigungu_code:
        lookups.bdong[bdong_code] = (sigungu_code, _pick(raw, "bdong_name") or bdong_code)
    else:
        bdong_code = None

    large_code = _pick(raw, "large_code")
    middle_code = _pick(raw, "middle_code")
    if large_code and (name := _pick(raw, "large_name")):
        lookups.category_large[large_code] = name
    elif large_code:
        lookups.category_large[large_code] = large_code

    if middle_code and large_code:
        lookups.category_middle[middle_code] = (large_code, _pick(raw, "middle_name") or middle_code)
    else:
        middle_code = None

    if small_code and middle_code:
        lookups.category_small[small_code] = (middle_code, _pick(raw, "small_name") or small_code)
    else:
        small_code = None

    if industry_code and (name := _pick(raw, "industry_name")):
        lookups.standard_industry[industry_code] = name
    elif industry_code:
        lookups.standard_industry[industry_code] = industry_code

    try:
        lon_val, lat_val = float(longitude), float(latitude)
    except ValueError:
        return None

    return StoreRow(
        store_number=store_number,
        store_name=store_name,
        branch_name=_pick(raw, "branch_name"),
        small_code=small_code,
        adong_code=adong_code,
        bdong_code=bdong_code,
        industry_code=industry_code,
        road_address=_pick(raw, "road_address"),
        jibun_address=_pick(raw, "jibun_address"),
        longitude=lon_val,
        latitude=lat_val,
    )
