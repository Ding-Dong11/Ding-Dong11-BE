"""주소 → WGS84 좌표 지오코딩. 카카오 로컬(1순위) + VWorld(fallback).

카카오를 1순위로 쓰는 이유(설계 결정):
- 카카오 로컬 주소검색 API 는 결과를 WGS84(경도/위도)로 직접 반환해 별도 좌표계
  변환이 필요 없다 (stores/sale_stores 와 동일 좌표계라 파이프라인 실패 지점이 준다).
- 단일 호출로 좌표를 얻는다 (행안부 방식은 주소검색→좌표조회 2단계가 필요).
VWorld 는 카카오가 결과를 못 찾거나 장애일 때만 보조로 사용한다.
"""
from __future__ import annotations

import httpx
from sqlalchemy import Engine

from app.etl.client.http import EtlHttpClient
from app.etl.geocode.cache import get_cached, set_cached

_KAKAO_URL = "https://dapi.kakao.com/v2/local/search/address.json"
_VWORLD_URL = "https://api.vworld.kr/req/address"


def _geocode_kakao(client: EtlHttpClient, address: str, api_key: str) -> tuple[float, float] | None:
    if not api_key:
        return None
    try:
        response = client.get(
            _KAKAO_URL,
            params={"query": address},
            headers={"Authorization": f"KakaoAK {api_key}"},
        )
    except httpx.HTTPError:
        # 잘못된 키(401)/요청 오류(400)/타임아웃·연결 실패 등 — VWorld fallback 으로 넘어가도록 무시
        return None

    documents = response.json().get("documents", [])
    if not documents:
        return None
    doc = documents[0]
    return float(doc["x"]), float(doc["y"])


def _geocode_vworld(client: EtlHttpClient, address: str, api_key: str) -> tuple[float, float] | None:
    if not api_key:
        return None
    try:
        response = client.get(
            _VWORLD_URL,
            params={
                "service": "address",
                "request": "getCoord",
                "format": "json",
                "type": "road",
                "crs": "epsg:4326",
                "address": address,
                "key": api_key,
            },
        )
    except httpx.HTTPError:
        return None

    body = response.json()
    result = body.get("response", {})
    if result.get("status") != "OK":
        return None
    point = result.get("result", {}).get("point", {})
    if not point:
        return None
    return float(point["x"]), float(point["y"])


def geocode_address(
    engine: Engine,
    http_client: EtlHttpClient,
    address: str,
    kakao_key: str,
    vworld_key: str,
    ttl_seconds: int,
) -> tuple[float | None, float | None]:
    """주소를 WGS84 (longitude, latitude) 로 변환. 실패 시 (None, None)."""
    if not address:
        return None, None

    cached = get_cached(engine, address, ttl_seconds)
    if cached is not None:
        return cached

    coords = _geocode_kakao(http_client, address, kakao_key)
    provider = "kakao"
    if coords is None:
        coords = _geocode_vworld(http_client, address, vworld_key)
        provider = "vworld"

    lon, lat = coords if coords is not None else (None, None)
    set_cached(engine, address, provider, (lon, lat))
    return lon, lat
