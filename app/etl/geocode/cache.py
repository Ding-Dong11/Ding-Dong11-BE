"""지오코딩 결과 캐시 (raw_geocode_cache 테이블).

동일 주소를 반복 지오코딩하지 않도록 영구 캐시하되, GEOCODE_CACHE_TTL_SECONDS
경과 시에는 재조회한다(주소 자체가 바뀌는 경우는 드물지만 프로바이더 정확도
개선 등을 반영할 여지를 둠).
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.etl.schema import raw_geocode_cache


def hash_address(address: str) -> str:
    return hashlib.sha256(address.strip().encode("utf-8")).hexdigest()


def get_cached(engine: Engine, address: str, ttl_seconds: int) -> tuple[float | None, float | None] | None:
    address_hash = hash_address(address)
    with engine.begin() as conn:
        row = conn.execute(
            select(raw_geocode_cache.c.longitude, raw_geocode_cache.c.latitude, raw_geocode_cache.c.created_at)
            .where(raw_geocode_cache.c.address_hash == address_hash)
        ).first()

    if row is None:
        return None

    if row.created_at is not None:
        cutoff = datetime.now(UTC) - timedelta(seconds=ttl_seconds)
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at < cutoff:
            return None

    return (float(row.longitude) if row.longitude is not None else None,
            float(row.latitude) if row.latitude is not None else None)


def set_cached(
    engine: Engine,
    address: str,
    provider: str,
    coords: tuple[float | None, float | None],
) -> None:
    address_hash = hash_address(address)
    longitude, latitude = coords
    with engine.begin() as conn:
        conn.execute(
            pg_insert(raw_geocode_cache).values(
                address_hash=address_hash,
                address_text=address[:300],
                provider=provider,
                longitude=longitude,
                latitude=latitude,
                created_at=datetime.now(UTC),
            )
            .on_conflict_do_update(
                index_elements=[raw_geocode_cache.c.address_hash],
                set_={
                    "provider": provider,
                    "longitude": longitude,
                    "latitude": latitude,
                    "created_at": datetime.now(UTC),
                },
            )
        )
