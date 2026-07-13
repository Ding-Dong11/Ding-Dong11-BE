from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, insert, update

from app.etl.schema import etl_run


@dataclass
class LoadResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    def __iadd__(self, other: LoadResult) -> LoadResult:
        self.inserted += other.inserted
        self.updated += other.updated
        self.skipped += other.skipped
        return self


@dataclass
class RunStats:
    extracted: int = 0
    loaded: LoadResult = field(default_factory=LoadResult)
    failed: int = 0


def chunked(iterable: Iterable[Any], size: int) -> Iterator[list[Any]]:
    chunk: list[Any] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


@contextmanager
def track_etl_run(engine: Engine, source: str):
    """etl_run 이력 테이블에 실행 시작/종료를 기록한다.

    실패 시에도 반드시 FAILED 상태와 에러 메시지를 남겨, 다음 실행에서
    원인 파악이 가능하게 한다.
    """
    stats = RunStats()
    with engine.begin() as conn:
        run_id = conn.execute(
            insert(etl_run).values(source=source, status="RUNNING").returning(etl_run.c.run_id)
        ).scalar_one()

    try:
        yield stats
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                update(etl_run)
                .where(etl_run.c.run_id == run_id)
                .values(
                    status="FAILED",
                    finished_at=datetime.now(UTC),
                    extracted_count=stats.extracted,
                    loaded_count=stats.loaded.inserted + stats.loaded.updated,
                    failed_count=stats.failed + 1,
                    error=str(exc),
                )
            )
        raise
    else:
        with engine.begin() as conn:
            conn.execute(
                update(etl_run)
                .where(etl_run.c.run_id == run_id)
                .values(
                    status="SUCCESS",
                    finished_at=datetime.now(UTC),
                    extracted_count=stats.extracted,
                    loaded_count=stats.loaded.inserted + stats.loaded.updated,
                    failed_count=stats.failed,
                )
            )
