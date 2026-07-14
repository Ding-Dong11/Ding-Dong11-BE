#!/usr/bin/env python3
"""stores.image_url 를 카카오 장소 검색으로 채우는 one-shot 스크립트.

동작 방식:
  1. DB에서 image_url IS NULL 인 stores 조회
  2. 각 store 마다 카카오 키워드 검색 API 로 좌표 기반 장소 탐색
  3. 첫 결과의 place_id 로 카카오 장소 상세 API(비공식) 호출 → 대표 이미지 URL 획득
  4. 획득한 URL 을 stores.image_url 에 업데이트

Usage:
    uv run python scripts/fill_store_images.py
    uv run python scripts/fill_store_images.py --limit 500 --delay 0.5
    uv run python scripts/fill_store_images.py --limit 100 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.database import get_engine
from app.models.reward import Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
_KAKAO_PLACE_MAIN_URL = "https://place.map.kakao.com/main/v/{place_id}"
_KAKAO_PLACE_HTML_URL = "https://place.map.kakao.com/{place_id}"
# OG image 정규식 — HTML fallback 용
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_IMAGE_RE2 = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.I,
)


def _search_kakao_place(
    client: httpx.Client, api_key: str, store_name: str, lon: float, lat: float
) -> str | None:
    """카카오 키워드 검색으로 place_id 반환. 결과 없으면 None. HTTP 오류는 호출자로 전파."""
    resp = client.get(
        _KAKAO_KEYWORD_URL,
        params={
            "query": store_name,
            "x": str(lon),
            "y": str(lat),
            "radius": 100,  # 100m 이내 우선 탐색
            "size": 1,
        },
        headers={"Authorization": f"KakaoAK {api_key}"},
        timeout=10,
    )
    resp.raise_for_status()

    docs = resp.json().get("documents", [])
    if not docs:
        return None
    return docs[0].get("id")


def _get_image_from_place_api(client: httpx.Client, place_id: str) -> str | None:
    """카카오 장소 상세 API(비공식 JSON)에서 대표 이미지 URL 반환."""
    try:
        resp = client.get(
            _KAKAO_PLACE_MAIN_URL.format(place_id=place_id),
            headers={
                "Referer": "https://map.kakao.com/",
                "User-Agent": "Mozilla/5.0 (compatible; store-image-filler/1.0)",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    data = resp.json()
    # 비공식 API 응답 구조: place > basicInfo > photoList > [0] > pc/mobile > url
    try:
        photo_list = (
            data.get("result", {})
            .get("place", {})
            .get("basicInfo", {})
            .get("photoList", [])
        )
        if photo_list:
            pc_info = photo_list[0].get("pc", {})
            url = pc_info.get("url") or pc_info.get("listurl")
            if url:
                return url
    except (AttributeError, IndexError, KeyError):
        pass
    return None


def _get_image_from_place_html(client: httpx.Client, place_id: str) -> str | None:
    """카카오 장소 HTML 페이지에서 og:image 태그 추출 (fallback)."""
    try:
        resp = client.get(
            _KAKAO_PLACE_HTML_URL.format(place_id=place_id),
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; store-image-filler/1.0)",
            },
            follow_redirects=True,
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    html = resp.text
    m = _OG_IMAGE_RE.search(html) or _OG_IMAGE_RE2.search(html)
    if m:
        url = m.group(1).strip()
        # 기본 OG 이미지(카카오 로고 등)는 제외
        if "kakao.com/static" in url or "kakaomap" in url:
            return None
        return url
    return None


def _get_place_image(client: httpx.Client, place_id: str) -> str | None:
    """JSON API 우선, 실패 시 HTML fallback."""
    url = _get_image_from_place_api(client, place_id)
    if url:
        return url
    return _get_image_from_place_html(client, place_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="stores.image_url 카카오 이미지로 채우기")
    parser.add_argument("--limit", type=int, default=0, help="처리할 상가 수 (0=전체)")
    parser.add_argument("--delay", type=float, default=0.3, help="요청 사이 딜레이(초)")
    parser.add_argument(
        "--dry-run", action="store_true", help="DB 업데이트 없이 로그만 출력"
    )
    args = parser.parse_args()

    settings = get_settings()
    api_key = settings.kakao_rest_api_key
    if not api_key:
        log.error("KAKAO_REST_API_KEY 가 설정되지 않았습니다.")
        sys.exit(1)

    engine = get_engine()

    # image_url IS NULL 인 store 목록 조회
    with engine.connect() as conn:
        stmt = select(
            Store.store_id,
            Store.store_name,
            Store.longitude,
            Store.latitude,
        ).where(Store.image_url.is_(None))
        if args.limit > 0:
            stmt = stmt.limit(args.limit)
        rows = conn.execute(stmt).mappings().all()

    total = len(rows)
    log.info("처리 대상 상가: %d 건", total)
    if total == 0:
        log.info("모든 상가에 이미지가 이미 채워져 있습니다.")
        return

    updated = 0
    not_found = 0
    errors = 0
    _BATCH_SIZE = 50  # 몇 건마다 DB commit

    pending: list[tuple[int, str]] = []  # (store_id, image_url)

    def _flush(conn_ctx) -> None:
        """pending 목록을 DB에 커밋하고 비운다."""
        if not pending or args.dry_run:
            pending.clear()
            return
        for sid, url in pending:
            conn_ctx.execute(
                update(Store).where(Store.store_id == sid).values(image_url=url)
            )
        conn_ctx.commit()
        pending.clear()

    with httpx.Client() as client, engine.connect() as conn:
        for i, row in enumerate(rows, 1):
            store_id = row["store_id"]
            store_name = row["store_name"]
            lon = float(row["longitude"])
            lat = float(row["latitude"])

            if i % 50 == 0:
                log.info("[%d/%d] 처리 중... (업데이트: %d, 미발견: %d, 오류: %d)", i, total, updated, not_found, errors)

            try:
                # 1) 카카오 키워드 검색
                place_id = _search_kakao_place(client, api_key, store_name, lon, lat)
            except httpx.HTTPError as e:
                log.warning("카카오 검색 HTTP 오류 [%s]: %s", store_name, e)
                errors += 1
                time.sleep(args.delay)
                continue

            if not place_id:
                log.debug("장소 미발견: %s (store_id=%d)", store_name, store_id)
                not_found += 1
                time.sleep(args.delay)
                continue

            # 2) 이미지 URL 획득
            image_url = _get_place_image(client, place_id)
            if not image_url:
                log.debug("이미지 없음: %s (place_id=%s)", store_name, place_id)
                not_found += 1
                time.sleep(args.delay)
                continue

            log.debug("이미지 획득: %s → %s", store_name, image_url[:80])
            pending.append((store_id, image_url))
            updated += 1

            # _BATCH_SIZE 마다 커밋
            if len(pending) >= _BATCH_SIZE:
                _flush(conn)

            time.sleep(args.delay)

        # 남은 건 최종 커밋
        _flush(conn)

    log.info(
        "완료 — 업데이트: %d, 이미지 없음/미발견: %d, 오류: %d (전체 %d 건)",
        updated,
        not_found,
        errors,
        total,
    )
    if args.dry_run:
        log.info("[dry-run] DB 업데이트는 실행되지 않았습니다.")


if __name__ == "__main__":
    main()
