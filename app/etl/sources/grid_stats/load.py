from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.etl.base import LoadResult
from app.etl.schema import grid_stat_metrics, grid_stat_values, grid_stats
from app.etl.sources.grid_stats.transform import GridStatRow, GridStatValueRow


def upsert_metrics(engine: Engine, metric_names: dict[str, str]) -> None:
    """코드집 xlsx 에서 뽑은 전체 통계항목코드->이름 매핑을 한 번에 upsert."""
    if not metric_names:
        return
    stmt = pg_insert(grid_stat_metrics).values(
        [{"metric_code": code, "metric_name": name, "unit": None} for code, name in metric_names.items()]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[grid_stat_metrics.c.metric_code],
        set_={"metric_name": stmt.excluded.metric_name},
    )
    with engine.begin() as conn:
        conn.execute(stmt)


def upsert_grid_stats(engine: Engine, rows: list[GridStatRow]) -> LoadResult:
    if not rows:
        return LoadResult()

    stmt = pg_insert(grid_stats).values(
        [
            {
                "grid_id": r.grid_id,
                "center_longitude": r.center_longitude,
                "center_latitude": r.center_latitude,
                "min_x": r.min_x,
                "min_y": r.min_y,
                "max_x": r.max_x,
                "max_y": r.max_y,
            }
            for r in rows
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[grid_stats.c.grid_id],
        set_={
            "center_longitude": stmt.excluded.center_longitude,
            "center_latitude": stmt.excluded.center_latitude,
            "min_x": stmt.excluded.min_x,
            "min_y": stmt.excluded.min_y,
            "max_x": stmt.excluded.max_x,
            "max_y": stmt.excluded.max_y,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)

    return LoadResult(inserted=len(rows))


def upsert_grid_stat_values(engine: Engine, rows: list[GridStatValueRow]) -> LoadResult:
    if not rows:
        return LoadResult()

    stmt = pg_insert(grid_stat_values).values(
        [{"grid_id": r.grid_id, "metric_code": r.metric_code, "value": r.value} for r in rows]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[grid_stat_values.c.grid_id, grid_stat_values.c.metric_code],
        set_={"value": stmt.excluded.value},
    )
    with engine.begin() as conn:
        conn.execute(stmt)

    return LoadResult(inserted=len(rows))
