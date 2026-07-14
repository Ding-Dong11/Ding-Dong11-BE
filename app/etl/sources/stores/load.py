from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.etl.base import LoadResult
from app.etl.schema import (
    adong,
    bdong,
    category_large,
    category_middle,
    category_small,
    sido,
    sigungu,
    standard_industry,
    stores,
)
from app.etl.sources.stores.excluded_industries import is_excluded
from app.etl.sources.stores.transform import LookupRows, StoreRow


def upsert_lookups(engine: Engine, lookups: LookupRows) -> None:
    with engine.begin() as conn:
        if lookups.sido:
            conn.execute(
                pg_insert(sido)
                .values([{"sido_code": k, "sido_name": v} for k, v in lookups.sido.items()])
                .on_conflict_do_update(
                    index_elements=[sido.c.sido_code],
                    set_={"sido_name": pg_insert(sido).excluded.sido_name},
                )
            )
        if lookups.sigungu:
            conn.execute(
                pg_insert(sigungu)
                .values(
                    [
                        {"sigungu_code": k, "sido_code": v[0], "sigungu_name": v[1]}
                        for k, v in lookups.sigungu.items()
                    ]
                )
                .on_conflict_do_update(
                    index_elements=[sigungu.c.sigungu_code],
                    set_={
                        "sido_code": pg_insert(sigungu).excluded.sido_code,
                        "sigungu_name": pg_insert(sigungu).excluded.sigungu_name,
                    },
                )
            )
        if lookups.adong:
            conn.execute(
                pg_insert(adong)
                .values(
                    [
                        {"adong_code": k, "sigungu_code": v[0], "adong_name": v[1]}
                        for k, v in lookups.adong.items()
                    ]
                )
                .on_conflict_do_update(
                    index_elements=[adong.c.adong_code],
                    set_={
                        "sigungu_code": pg_insert(adong).excluded.sigungu_code,
                        "adong_name": pg_insert(adong).excluded.adong_name,
                    },
                )
            )
        if lookups.bdong:
            conn.execute(
                pg_insert(bdong)
                .values(
                    [
                        {"bdong_code": k, "sigungu_code": v[0], "bdong_name": v[1]}
                        for k, v in lookups.bdong.items()
                    ]
                )
                .on_conflict_do_update(
                    index_elements=[bdong.c.bdong_code],
                    set_={
                        "sigungu_code": pg_insert(bdong).excluded.sigungu_code,
                        "bdong_name": pg_insert(bdong).excluded.bdong_name,
                    },
                )
            )
        if lookups.category_large:
            conn.execute(
                pg_insert(category_large)
                .values(
                    [{"large_code": k, "large_name": v} for k, v in lookups.category_large.items()]
                )
                .on_conflict_do_update(
                    index_elements=[category_large.c.large_code],
                    set_={"large_name": pg_insert(category_large).excluded.large_name},
                )
            )
        if lookups.category_middle:
            conn.execute(
                pg_insert(category_middle)
                .values(
                    [
                        {"middle_code": k, "large_code": v[0], "middle_name": v[1]}
                        for k, v in lookups.category_middle.items()
                    ]
                )
                .on_conflict_do_update(
                    index_elements=[category_middle.c.middle_code],
                    set_={
                        "large_code": pg_insert(category_middle).excluded.large_code,
                        "middle_name": pg_insert(category_middle).excluded.middle_name,
                    },
                )
            )
        if lookups.category_small:
            conn.execute(
                pg_insert(category_small)
                .values(
                    [
                        {"small_code": k, "middle_code": v[0], "small_name": v[1]}
                        for k, v in lookups.category_small.items()
                    ]
                )
                .on_conflict_do_update(
                    index_elements=[category_small.c.small_code],
                    set_={
                        "middle_code": pg_insert(category_small).excluded.middle_code,
                        "small_name": pg_insert(category_small).excluded.small_name,
                    },
                )
            )
        if lookups.standard_industry:
            conn.execute(
                pg_insert(standard_industry)
                .values(
                    [
                        {"industry_code": k, "industry_name": v}
                        for k, v in lookups.standard_industry.items()
                    ]
                )
                .on_conflict_do_update(
                    index_elements=[standard_industry.c.industry_code],
                    set_={"industry_name": pg_insert(standard_industry).excluded.industry_name},
                )
            )


def upsert_stores(engine: Engine, rows: list[StoreRow]) -> LoadResult:
    if not rows:
        return LoadResult()

    rows = [r for r in rows if not is_excluded(r.industry_code)]
    if not rows:
        return LoadResult()

    values = [
        {
            "store_number": r.store_number,
            "store_name": r.store_name,
            "branch_name": r.branch_name,
            "small_code": r.small_code,
            "adong_code": r.adong_code,
            "bdong_code": r.bdong_code,
            "industry_code": r.industry_code,
            "road_address": r.road_address,
            "jibun_address": r.jibun_address,
            "longitude": r.longitude,
            "latitude": r.latitude,
        }
        for r in rows
    ]

    stmt = pg_insert(stores).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[stores.c.store_number],
        set_={
            "store_name": stmt.excluded.store_name,
            "branch_name": stmt.excluded.branch_name,
            "small_code": stmt.excluded.small_code,
            "adong_code": stmt.excluded.adong_code,
            "bdong_code": stmt.excluded.bdong_code,
            "industry_code": stmt.excluded.industry_code,
            "road_address": stmt.excluded.road_address,
            "jibun_address": stmt.excluded.jibun_address,
            "longitude": stmt.excluded.longitude,
            "latitude": stmt.excluded.latitude,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)

    return LoadResult(inserted=len(rows))
