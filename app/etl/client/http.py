"""공공 API 호출용 공통 HTTP 클라이언트: 타임아웃/재시도/rate-limit."""
from __future__ import annotations

import time

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings


class RateLimiter:
    """초당 호출 수를 제한하는 최소 간격 방식 리미터."""

    def __init__(self, per_sec: float) -> None:
        self._min_interval = 1.0 / per_sec if per_sec > 0 else 0.0
        self._last_call: float | None = None

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        if self._last_call is not None:
            elapsed = now - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call = time.monotonic()


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


class EtlHttpClient:
    """재시도/rate-limit 이 적용된 동기 HTTP 클라이언트 래퍼."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=settings.etl_http_timeout)
        self._limiter = RateLimiter(settings.etl_rate_limit_per_sec)

    def get(
        self, url: str, params: dict | None = None, headers: dict | None = None
    ) -> httpx.Response:
        @retry(
            stop=stop_after_attempt(self._settings.etl_max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )
        def _do_get() -> httpx.Response:
            self._limiter.wait()
            response = self._client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response

        return _do_get()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EtlHttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
