"""국토지리정보원/SGIS 격자 통계 및 경계 추출.

실제 배포본 구조 (CSV 한 장짜리 wide 포맷이 아니라 3종으로 분리됨):
- 경계(boundary): 지역 코드별 폴더(grid_XX/grid_XX_1K.{shp,dbf,shx,prj,cpg}) 안의
  ESRI Shapefile. 속성은 GRID_CD(격자코드) 하나뿐이고, 좌표는 EPSG:5179(투영좌표,
  .prj로 확인됨) 미터 단위 폴리곤 — 정사각형 격자라 bbox 자체가 min/max, 중심은
  bbox 중점으로 계산해도 정확하다.
- 통계(statistics): 카테고리별(인구/가구/주택/사업체 등) 폴더 아래 지역별 CSV.
  이미 (기준연도, 격자코드, 통계항목코드, 통계값) long 포맷(cp949)이라 그대로 사용.
- 코드집(codes): xlsx "격자" 시트에 통계항목코드 -> 통계항목명 매핑.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import shapefile

STATS_ENCODING = "cp949"


def extract_boundary(boundary_root: Path) -> Iterator[dict[str, Any]]:
    """boundary_root 이하 모든 *.shp 를 순회해 격자별 bbox 를 yield."""
    for shp_path in sorted(boundary_root.rglob("*.shp")):
        reader = shapefile.Reader(str(shp_path), encoding="utf-8")
        for shape_record in reader.iterShapeRecords():
            xmin, ymin, xmax, ymax = shape_record.shape.bbox
            yield {
                "grid_id": shape_record.record["GRID_CD"],
                "min_x": xmin,
                "min_y": ymin,
                "max_x": xmax,
                "max_y": ymax,
            }


def extract_statistics(stats_root: Path) -> Iterator[dict[str, Any]]:
    """stats_root 이하 모든 *.csv 를 순회해 (기준연도, 격자코드, 통계항목, 통계값) 행을 yield."""
    import csv

    for csv_path in sorted(stats_root.rglob("*.csv")):
        with csv_path.open(encoding=STATS_ENCODING, newline="") as f:
            reader = csv.DictReader(f)
            yield from reader


def load_metric_names(codes_xlsx: Path, sheet_name: str = "격자") -> dict[str, str]:
    """코드집 xlsx 의 '격자' 시트에서 통계항목코드 -> 통계항목명 매핑을 만든다."""
    import openpyxl

    wb = openpyxl.load_workbook(codes_xlsx, read_only=True, data_only=True)
    ws = wb[sheet_name]

    names: dict[str, str] = {}
    for row in ws.iter_rows(values_only=True):
        if len(row) < 5:
            continue
        metric_name, metric_code = row[3], row[4]
        if not metric_code or not isinstance(metric_code, str):
            continue
        if metric_name:
            names[metric_code] = str(metric_name)
    return names
