from __future__ import annotations

import json
from typing import Generator

import anthropic
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.redis_keys import chat_history_key
from app.repositories.reward import RewardRepository

_BASE_SYSTEM_PROMPT = """당신은 Ding-Dong 앱의 AI 어시스턴트입니다.

Ding-Dong 앱은 다음 기능을 제공합니다:
- 주변 상가 정보를 지도에서 확인하고 QR 코드 인증으로 포인트를 적립
- 동네 마트/가게의 마감할인 세일 상품 목록 확인
- 적립한 포인트로 쿠폰 교환
- 행정처분 이력이 있는 식품접객업체 정보 조회

사용자가 상가 추천, 세일 정보, 포인트 사용 방법, 앱 이용 방법 등을 물어보면 친절하고 명확하게 한국어로 답변하세요.
구체적인 실시간 상가 정보나 재고 현황은 앱 내 지도/피드 화면을 이용하도록 안내하세요."""

_MAX_HISTORY = 20
_HISTORY_TTL = 86400


class ChatService:
    def __init__(self, redis: Redis, settings: Settings, db: Session):
        self.redis = redis
        self.settings = settings
        self.db = db

    # ── 이력 관리 ────────────────────────────────────────────────────────────

    def get_history(self, user_id: int) -> list[dict]:
        raw = self.redis.get(chat_history_key(user_id))
        if raw is None:
            return []
        return json.loads(raw)

    def clear_history(self, user_id: int) -> None:
        self.redis.delete(chat_history_key(user_id))

    def _save_history(self, user_id: int, history: list[dict]) -> None:
        trimmed = history[-_MAX_HISTORY:]
        self.redis.set(
            chat_history_key(user_id),
            json.dumps(trimmed, ensure_ascii=False),
            ex=_HISTORY_TTL,
        )

    # ── 개인화 추천 컨텍스트 ─────────────────────────────────────────────────

    def _build_recommendation_context(self, user_id: int) -> str:
        """사용자 QR 인증 이력 기반 개인화 추천 컨텍스트 생성.

        같은 업종 중 방문자(reward_verifications)가 적은 상가를 우선 나열.
        이 텍스트를 시스템 프롬프트에 덧붙여 Claude에 전달한다.
        """
        repo = RewardRepository(self.db)

        verified_ids = repo.get_user_verified_store_ids(user_id)
        if not verified_ids:
            return ""

        small_codes = repo.get_user_verified_small_codes(user_id)
        if not small_codes:
            return ""

        similar = repo.list_similar_stores_ranked(
            small_codes=small_codes,
            exclude_store_ids=verified_ids,
            limit=10,
        )
        if not similar:
            return ""

        lines = [
            "",
            "[개인화 추천 컨텍스트]",
            f"이 사용자는 총 {len(verified_ids)}개 상가에서 QR 인증을 완료했습니다.",
            "동일 업종의 미방문 상가 목록 (방문자 수 오름차순 — 덜 알려진 숨은 명소 우선):",
        ]
        for i, (store, count) in enumerate(similar, 1):
            addr = store.road_address or store.jibun_address or "주소 미상"
            lines.append(
                f"{i}. {store.store_name} | 주소: {addr} | 누적 방문자: {count}명"
            )
        lines += [
            "",
            "사용자가 '추천', '비슷한 곳', '어디 갈까', '새로운 곳' 등을 언급하면 "
            "위 목록을 참고해 자연스럽게 한국어로 소개하세요. "
            "방문자가 적은 상가는 아직 덜 알려진 숨은 명소일 수 있으니 긍정적으로 강조하세요.",
        ]
        return "\n".join(lines)

    # ── 스트리밍 메시지 ──────────────────────────────────────────────────────

    def stream_message(
        self, user_id: int, content: str
    ) -> Generator[str, None, None]:
        """사용자 메시지를 Claude에 전달하고 응답을 SSE 청크로 스트리밍.

        청크 형식: JSON 문자열
          - 중간: {"text": "...", "done": false}
          - 완료: {"text": "", "done": true}

        응답 완료 후 전체 대화 이력을 Redis에 저장(TTL 갱신).
        """
        history = self.get_history(user_id)
        history.append({"role": "user", "content": content})

        recommendation_ctx = self._build_recommendation_context(user_id)
        system_prompt = _BASE_SYSTEM_PROMPT + recommendation_ctx

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

        with client.messages.stream(
            model=self.settings.anthropic_model,
            max_tokens=5000,
            system=system_prompt,
            messages=history[-_MAX_HISTORY:],
            thinking={"type": "adaptive"},
        ) as stream:
            for text in stream.text_stream:
                yield json.dumps({"text": text, "done": False}, ensure_ascii=False)
            full_response = stream.get_final_text()

        history.append({"role": "assistant", "content": full_response})
        self._save_history(user_id, history)
        yield json.dumps({"text": "", "done": True}, ensure_ascii=False)
