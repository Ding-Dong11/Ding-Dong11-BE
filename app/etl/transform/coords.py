"""좌표계 변환: UTM-K(EPSG:5179, 국토지리정보원 격자) → WGS84(EPSG:4326)."""
from __future__ import annotations

from functools import lru_cache

from pyproj import Transformer


@lru_cache
def _utmk_to_wgs84() -> Transformer:
    # always_xy=True: 입출력 순서를 항상 (x, y) = (lon, lat) 로 고정
    return Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)


def utmk_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """UTM-K (x, y) -> WGS84 (longitude, latitude)."""
    lon, lat = _utmk_to_wgs84().transform(x, y)
    return lon, lat
