"""data.go.kr 공공데이터포털 공통 응답 규격 처리.

공공데이터포털 API 는 HTTP 200 이어도 header.resultCode 가 '00' 이 아니면
실패인 경우가 많아, 반드시 이 규격으로 파싱해 결과코드를 먼저 확인한다.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.etl.client.http import EtlHttpClient


class DataGoKrError(RuntimeError):
    def __init__(self, result_code: str, result_msg: str) -> None:
        super().__init__(f"data.go.kr API error [{result_code}] {result_msg}")
        self.result_code = result_code
        self.result_msg = result_msg


def _extract_body(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response", payload)
    header = response.get("header", {})
    result_code = str(header.get("resultCode", "00"))
    if result_code != "00":
        raise DataGoKrError(result_code, header.get("resultMsg", "unknown error"))
    return response.get("body", {})


def iter_pages(
    client: EtlHttpClient,
    url: str,
    params: dict[str, Any],
    service_key: str,
    page_size: int = 100,
) -> Iterator[list[dict[str, Any]]]:
    """totalCount/numOfRows/pageNo 기반 페이징 제너레이터."""
    page_no = 1
    fetched = 0
    total_count: int | None = None

    while True:
        page_params = {
            **params,
            "serviceKey": service_key,
            "pageNo": page_no,
            "numOfRows": page_size,
            "type": "json",
        }
        response = client.get(url, params=page_params)
        body = _extract_body(response.json())

        items_container = body.get("items", [])
        if isinstance(items_container, dict):
            items = items_container.get("item", [])
        else:
            items = items_container
        if isinstance(items, dict):
            items = [items]

        if not items:
            return

        yield items
        fetched += len(items)

        if total_count is None:
            total_count = int(body.get("totalCount", fetched))
        if fetched >= total_count or len(items) < page_size:
            return
        page_no += 1
