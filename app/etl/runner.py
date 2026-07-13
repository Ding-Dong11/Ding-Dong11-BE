from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine

from app.core.config import Settings
from app.etl.base import LoadResult, chunked, track_etl_run
from app.etl.client.http import EtlHttpClient
from app.etl.sources.dispositions import extract as disp_extract
from app.etl.sources.dispositions import load as disp_load
from app.etl.sources.dispositions import transform as disp_transform
from app.etl.sources.grid_stats import extract as grid_extract
from app.etl.sources.grid_stats import load as grid_load
from app.etl.sources.grid_stats import transform as grid_transform
from app.etl.sources.stores import extract as stores_extract
from app.etl.sources.stores import load as stores_load
from app.etl.sources.stores import transform as stores_transform


def run_stores_bulk(engine: Engine, settings: Settings, csv_path: Path) -> LoadResult:
    with track_etl_run(engine, "stores_csv") as stats:
        total = LoadResult()
        for raw_chunk in chunked(stores_extract.extract_csv(csv_path), settings.etl_chunk_size):
            lookups = stores_transform.LookupRows()
            rows = []
            for raw in raw_chunk:
                stats.extracted += 1
                row = stores_transform.transform_row(raw, lookups)
                if row is None:
                    stats.failed += 1
                    continue
                rows.append(row)

            stores_load.upsert_lookups(engine, lookups)
            result = stores_load.upsert_stores(engine, rows)
            stats.loaded += result
            total += result
        return total


def run_stores_api(
    engine: Engine, settings: Settings, http_client: EtlHttpClient, params: dict[str, Any] | None = None
) -> LoadResult:
    with track_etl_run(engine, "stores_api") as stats:
        total = LoadResult()
        raw_iter = stores_extract.extract_api(
            http_client,
            settings.data_go_kr_stores_api_url,
            settings.data_go_kr_service_key,
            params,
        )
        for raw_chunk in chunked(raw_iter, settings.etl_chunk_size):
            lookups = stores_transform.LookupRows()
            rows = []
            for raw in raw_chunk:
                stats.extracted += 1
                row = stores_transform.transform_row(raw, lookups)
                if row is None:
                    stats.failed += 1
                    continue
                rows.append(row)

            stores_load.upsert_lookups(engine, lookups)
            result = stores_load.upsert_stores(engine, rows)
            stats.loaded += result
            total += result
        return total


def run_grid_stats(
    engine: Engine,
    settings: Settings,
    boundary_dir: Path,
    stats_dir: Path,
    codes_xlsx: Path,
) -> LoadResult:
    """격자 경계(shapefile) + 통계(long CSV) + 코드집(xlsx) 을 함께 적재한다.

    FK(grid_stat_values.grid_id -> grid_stats.grid_id) 때문에 경계를 먼저 전량
    적재하고, 그 grid_id 집합을 알고 있어야 통계 쪽에서 참조 무결성이 깨지는
    행(경계 데이터에 없는 격자)을 걸러낼 수 있다.
    """
    metric_names = grid_extract.load_metric_names(codes_xlsx)
    grid_load.upsert_metrics(engine, metric_names)

    total = LoadResult()
    known_grid_ids: set[str] = set()

    with track_etl_run(engine, "grid_stats_boundary") as stats:
        for raw_chunk in chunked(grid_extract.extract_boundary(boundary_dir), settings.etl_chunk_size):
            grid_rows = []
            for raw in raw_chunk:
                stats.extracted += 1
                row = grid_transform.transform_boundary_row(raw)
                if row is None:
                    stats.failed += 1
                    continue
                grid_rows.append(row)
                known_grid_ids.add(row.grid_id)

            result = grid_load.upsert_grid_stats(engine, grid_rows)
            stats.loaded += result
            total += result

    with track_etl_run(engine, "grid_stats_values") as stats:
        for raw_chunk in chunked(grid_extract.extract_statistics(stats_dir), settings.etl_chunk_size):
            value_rows = []
            for raw in raw_chunk:
                stats.extracted += 1
                row = grid_transform.transform_statistics_row(raw)
                if row is None or row.grid_id not in known_grid_ids:
                    stats.failed += 1
                    continue
                value_rows.append(row)

            result = grid_load.upsert_grid_stat_values(engine, value_rows)
            stats.loaded += result
            total += result

    return total


def run_dispositions(
    engine: Engine,
    settings: Settings,
    http_client: EtlHttpClient,
    params: dict[str, Any] | None = None,
) -> LoadResult:
    with track_etl_run(engine, "dispositions") as stats:
        total = LoadResult()
        raw_iter = disp_extract.extract_api(
            http_client,
            settings.data_go_kr_dispositions_api_url,
            settings.data_go_kr_service_key,
            params,
        )
        for raw_chunk in chunked(raw_iter, settings.etl_chunk_size):
            rows = []
            for raw in raw_chunk:
                stats.extracted += 1
                row = disp_transform.transform_row(
                    raw,
                    engine,
                    http_client,
                    settings.kakao_rest_api_key,
                    settings.vworld_api_key,
                    settings.geocode_cache_ttl_seconds,
                )
                if row is None:
                    stats.failed += 1
                    continue
                rows.append(row)

            disp_load.upsert_disposition_types(engine, rows)
            result = disp_load.upsert_dispositions(engine, rows)
            stats.loaded += result
            total += result
        return total
