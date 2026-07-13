"""식약처 행정처분(식품접객업) Open API 추출."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.etl.client.datagokr import iter_pages
from app.etl.client.http import EtlHttpClient


def extract_api(
    client: EtlHttpClient,
    base_url: str,
    service_key: str,
    params: dict[str, Any] | None = None,
    page_size: int = 100,
) -> Iterator[dict[str, Any]]:
    for page in iter_pages(client, base_url, params or {}, service_key, page_size):
        yield from page
