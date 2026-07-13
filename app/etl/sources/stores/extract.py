"""소상공인시장진흥공단 상가(상권)정보: CSV 일괄(bulk) + Open API 증분(incremental)."""
from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from app.etl.client.datagokr import iter_pages
from app.etl.client.http import EtlHttpClient

# 공공데이터포털 "소상공인시장진흥공단_상가(상권)정보" CSV 인코딩.
# 배포본 README(파일열람방법.txt)에 따르면 과거 euc-kr 배포에서 업소명 인코딩 문제로
# UTF-8 로 전환됐다(2025년 기준). 향후 배포본이 바뀔 수 있어 호출부에서 override 가능.
CSV_ENCODING = "utf-8"


def extract_csv(path: Path) -> Iterator[dict[str, Any]]:
    """CSV 파일 하나 또는 지역별 CSV 가 담긴 디렉토리 전체를 읽는다 (초기 대량 적재).

    분기별 배포본은 지역(시도)별로 파일이 나뉘어 오므로 디렉토리를 받으면
    그 안의 모든 *.csv 를 순회한다.
    """
    paths = sorted(path.glob("*.csv")) if path.is_dir() else [path]
    for csv_path in paths:
        with csv_path.open(encoding=CSV_ENCODING, newline="") as f:
            reader = csv.DictReader(f)
            yield from reader


def extract_api(
    client: EtlHttpClient,
    base_url: str,
    service_key: str,
    params: dict[str, Any] | None = None,
    page_size: int = 100,
) -> Iterator[dict[str, Any]]:
    """증분 갱신용 Open API 페이징 (지역/업종 코드 등으로 params 필터링)."""
    for page in iter_pages(client, base_url, params or {}, service_key, page_size):
        yield from page
