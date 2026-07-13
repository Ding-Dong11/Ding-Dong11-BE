"""경계(shapefile bbox) -> grid_stats 행 / 통계(long CSV) -> grid_stat_values 행.

좌표는 UTM-K(EPSG:5179) 투영좌표 원본을 WGS84(EPSG:4326) 로 변환한다 (database.md).
격자가 정사각형이라 bbox 중점을 투영좌표 상에서 구한 뒤 한 번만 변환하면 중심좌표로
충분히 정확하다(변환의 비선형성으로 인한 오차는 1km 격자 크기에서 무시할 수준).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.etl.transform.coords import utmk_to_wgs84


@dataclass
class GridStatRow:
    grid_id: str
    center_longitude: float
    center_latitude: float
    min_x: float
    min_y: float
    max_x: float
    max_y: float


@dataclass
class GridStatValueRow:
    grid_id: str
    metric_code: str
    value: float


def transform_boundary_row(raw: dict[str, Any]) -> GridStatRow | None:
    grid_id = raw.get("grid_id")
    if not grid_id:
        return None

    min_x_utmk, min_y_utmk = raw["min_x"], raw["min_y"]
    max_x_utmk, max_y_utmk = raw["max_x"], raw["max_y"]
    center_x_utmk = (min_x_utmk + max_x_utmk) / 2
    center_y_utmk = (min_y_utmk + max_y_utmk) / 2

    min_lon, min_lat = utmk_to_wgs84(min_x_utmk, min_y_utmk)
    max_lon, max_lat = utmk_to_wgs84(max_x_utmk, max_y_utmk)
    center_lon, center_lat = utmk_to_wgs84(center_x_utmk, center_y_utmk)

    return GridStatRow(
        grid_id=str(grid_id),
        center_longitude=center_lon,
        center_latitude=center_lat,
        min_x=min_lon,
        min_y=min_lat,
        max_x=max_lon,
        max_y=max_lat,
    )


def transform_statistics_row(raw: dict[str, Any]) -> GridStatValueRow | None:
    grid_id = raw.get("격자코드")
    metric_code = raw.get("통계항목")
    value = raw.get("통계값")

    if not grid_id or not metric_code or value in (None, ""):
        return None

    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return None

    return GridStatValueRow(grid_id=str(grid_id), metric_code=str(metric_code), value=value_f)
