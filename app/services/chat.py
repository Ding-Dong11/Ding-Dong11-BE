"""AI 챗봇 서비스 — Claude Tool Use 기반 RAG 에이전틱 루프."""
from __future__ import annotations

import json
from typing import Generator

import anthropic
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.redis_keys import chat_history_key, chat_location_key
from app.repositories.chat_tool import ChatToolRepository

_MAX_HISTORY = 20
_HISTORY_TTL = 86400     # 24h
_LOCATION_TTL = 3600     # 1h
_MAX_TOOL_ROUNDS = 5

_BASE_SYSTEM_PROMPT = """당신은 Ding-Dong 앱의 AI 어시스턴트입니다. 항상 한국어로 답변하세요.

Ding-Dong 앱 주요 기능:
- 지도에서 주변 상가 확인 및 QR 인증으로 포인트 적립
- 동네 마트·가게의 마감할인 세일 상품 피드
- 포인트로 쿠폰 교환
- 행정처분(위생불량·영업정지 등) 이력이 있는 업체 정보 조회

당신은 다음 도구로 실시간 데이터에 접근할 수 있습니다:
- nearby_stores: 위치 기반 주변 상가 검색
- store_detail: 특정 상가 상세 (행정처분·할인상품 포함)
- nearby_sales: 주변 마감할인 세일 상품 조회
- search_dispositions: 행정처분 이력 검색
- my_recommendations: 사용자 맞춤 상가 추천

도구 사용 지침:
- 상가 추천·정보·세일 문의 등 실시간 데이터가 필요한 질문엔 반드시 도구를 호출하세요.
- 사용자가 특정 위치를 언급(예: '강남역 근처')하면 그 위치에 해당하는 좌표로 검색하세요.
  → 알 수 없는 위치명엔 현재 위치(아래 제공)를 기본으로 사용하세요.
- 도구 결과를 바탕으로 자연스럽고 친절하게 한국어로 설명하세요.
- 방문자가 적은 상가(숨은 명소)는 긍정적으로 소개하세요."""

# ── Tool Use 도구 정의 ────────────────────────────────────────────────────────

_CHAT_TOOLS: list[dict] = [
    {
        "name": "nearby_stores",
        "description": (
            "위치 기준 반경 내 상가 목록 조회. "
            "상가 추천·근처 가게 찾기·지역 상권 정보 요청에 사용. "
            "결과에 has_active_qr(QR 적립 가능), has_disposition(행정처분 이력), has_sale(할인 중) 플래그 포함."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "위도 (현재 위치 또는 사용자가 언급한 위치)"},
                "lon": {"type": "number", "description": "경도"},
                "radius_km": {"type": "number", "description": "검색 반경 km, 기본 1.0"},
                "query": {"type": "string", "description": "업종·상호명 키워드 (선택)"},
                "limit": {"type": "integer", "description": "최대 결과 수, 기본 10"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "store_detail",
        "description": (
            "특정 상가의 상세 정보 조회. "
            "행정처분 이력, 현재 할인 상품, QR 적립 여부 포함. "
            "nearby_stores 결과에서 store_id 를 얻은 후 호출."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": {"type": "integer", "description": "상가 ID (nearby_stores 결과에서 획득)"},
            },
            "required": ["store_id"],
        },
    },
    {
        "name": "nearby_sales",
        "description": (
            "주변 마감할인 세일 상품 조회. "
            "'오늘 세일', '할인 상품', '마감 임박' 등 키워드에 사용."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "위도"},
                "lon": {"type": "number", "description": "경도"},
                "radius_km": {"type": "number", "description": "검색 반경 km, 기본 2.0"},
                "query": {"type": "string", "description": "상품명 키워드 (선택)"},
                "limit": {"type": "integer", "description": "최대 결과 수, 기본 10"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "search_dispositions",
        "description": (
            "행정처분(영업정지·위생불량 등) 이력 검색. "
            "'행정처분', '위생 불량', '영업정지', '믿을 수 있는 가게' 등 문의에 사용. "
            "상호명 또는 업종 키워드로 검색."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색할 상호명 또는 업종 키워드"},
                "lat": {"type": "number", "description": "위도 (위치 기반 검색 시 선택)"},
                "lon": {"type": "number", "description": "경도 (위치 기반 검색 시 선택)"},
                "radius_km": {"type": "number", "description": "위치 기반 검색 반경 km, 기본 3.0"},
                "limit": {"type": "integer", "description": "최대 결과 수, 기본 10"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "my_recommendations",
        "description": (
            "사용자 QR 인증 이력 기반 맞춤 상가 추천. "
            "'추천해줘', '어디 갈까', '비슷한 곳', '새로운 곳' 등 개인화 추천 요청에 사용. "
            "방문하지 않은 동일 업종 상가를 방문자 수 오름차순(숨은 명소 우선)으로 반환."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "위도"},
                "lon": {"type": "number", "description": "경도"},
                "radius_km": {"type": "number", "description": "검색 반경 km, 기본 2.0"},
                "limit": {"type": "integer", "description": "최대 결과 수, 기본 10"},
            },
            "required": ["lat", "lon"],
        },
    },
]


# ── 내용 블록 직렬화 헬퍼 ────────────────────────────────────────────────────

def _serialize_content(blocks) -> list[dict]:
    """Anthropic 응답 ContentBlock 리스트를 API 재사용 가능한 dict 리스트로 변환."""
    result = []
    for block in blocks:
        t = block.type
        if t == "text":
            result.append({"type": "text", "text": block.text})
        elif t == "tool_use":
            result.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
        elif t == "thinking":
            result.append({"type": "thinking", "thinking": block.thinking})
        elif t == "redacted_thinking":
            result.append({"type": "redacted_thinking", "data": block.data})
    return result


class ChatService:
    def __init__(self, redis: Redis, settings: Settings, db: Session):
        self.redis = redis
        self.settings = settings
        self.db = db
        self._tool_repo = ChatToolRepository(db)

    # ── 위치 관리 ─────────────────────────────────────────────────────────────

    def _get_location(self, user_id: int, lat: float | None, lon: float | None) -> tuple[float, float] | None:
        """현재 위치를 반환하고 Redis에 갱신. 없으면 캐시에서 복원."""
        if lat is not None and lon is not None:
            self.redis.set(
                chat_location_key(user_id),
                json.dumps({"lat": lat, "lon": lon}),
                ex=_LOCATION_TTL,
            )
            return lat, lon

        cached = self.redis.get(chat_location_key(user_id))
        if cached:
            d = json.loads(cached)
            return d["lat"], d["lon"]
        return None

    # ── 이력 관리 ─────────────────────────────────────────────────────────────

    def get_history(self, user_id: int) -> list[dict]:
        raw = self.redis.get(chat_history_key(user_id))
        return json.loads(raw) if raw else []

    def clear_history(self, user_id: int) -> None:
        self.redis.delete(chat_history_key(user_id))

    def _save_history(self, user_id: int, history: list[dict]) -> None:
        trimmed = history[-_MAX_HISTORY:]
        self.redis.set(
            chat_history_key(user_id),
            json.dumps(trimmed, ensure_ascii=False),
            ex=_HISTORY_TTL,
        )

    # ── 시스템 프롬프트 구성 ───────────────────────────────────────────────────

    def _build_system_prompt(self, location: tuple[float, float] | None) -> str:
        parts = [_BASE_SYSTEM_PROMPT]
        if location:
            lat, lon = location
            parts.append(f"\n[현재 사용자 위치] 위도 {lat:.6f}, 경도 {lon:.6f}")
            parts.append("위치 정보가 없는 질문에는 이 좌표를 기준으로 도구를 호출하세요.")
        else:
            parts.append("\n[현재 사용자 위치] 알 수 없음 — 위치 관련 질문에는 사용자에게 위치 공유를 요청하세요.")
        return "\n".join(parts)

    # ── 도구 실행 디스패처 ─────────────────────────────────────────────────────

    def _execute_tool(
        self,
        name: str,
        tool_input: dict,
        user_id: int,
        location: tuple[float, float] | None,
    ) -> str:
        """도구 이름과 입력을 받아 실행 후 JSON 문자열로 반환."""
        default_lat = location[0] if location else None
        default_lon = location[1] if location else None
        _NO_LOC = {"error": "위치 정보가 없습니다. 위치를 공유해 주세요."}

        try:
            if name == "nearby_stores":
                lat_v = tool_input.get("lat", default_lat)
                lon_v = tool_input.get("lon", default_lon)
                if lat_v is None or lon_v is None:
                    result = _NO_LOC
                else:
                    result = self._tool_repo.nearby_stores(
                        lat=lat_v,
                        lon=lon_v,
                        radius_km=tool_input.get("radius_km", 1.0),
                        query=tool_input.get("query"),
                        limit=tool_input.get("limit", 10),
                    )

            elif name == "store_detail":
                result = self._tool_repo.store_detail(tool_input["store_id"])
                if result is None:
                    result = {"error": "해당 상가를 찾을 수 없습니다."}

            elif name == "nearby_sales":
                lat_v = tool_input.get("lat", default_lat)
                lon_v = tool_input.get("lon", default_lon)
                if lat_v is None or lon_v is None:
                    result = _NO_LOC
                else:
                    result = self._tool_repo.nearby_sales(
                        lat=lat_v,
                        lon=lon_v,
                        radius_km=tool_input.get("radius_km", 2.0),
                        query=tool_input.get("query"),
                        limit=tool_input.get("limit", 10),
                    )

            elif name == "search_dispositions":
                result = self._tool_repo.search_dispositions(
                    query=tool_input["query"],
                    lat=tool_input.get("lat", default_lat),
                    lon=tool_input.get("lon", default_lon),
                    radius_km=tool_input.get("radius_km", 3.0),
                    limit=tool_input.get("limit", 10),
                )

            elif name == "my_recommendations":
                lat_v = tool_input.get("lat", default_lat)
                lon_v = tool_input.get("lon", default_lon)
                if lat_v is None or lon_v is None:
                    result = _NO_LOC
                else:
                    result = self._tool_repo.my_recommendations(
                        user_id=user_id,
                        lat=lat_v,
                        lon=lon_v,
                        radius_km=tool_input.get("radius_km", 2.0),
                        limit=tool_input.get("limit", 10),
                    )

            else:
                result = {"error": f"알 수 없는 도구: {name}"}

        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc)}

        return json.dumps(result, ensure_ascii=False, default=str)

    # ── 스트리밍 메시지 (Tool Use 에이전틱 루프) ─────────────────────────────

    def stream_message(
        self,
        user_id: int,
        content: str,
        lat: float | None = None,
        lon: float | None = None,
    ) -> Generator[str, None, None]:
        """Claude Tool Use 루프로 메시지 처리 후 응답을 SSE 청크로 스트리밍.

        청크 형식:
          - 중간: {"text": "...", "done": false}
          - 완료: {"text": "", "done": true}

        각 라운드의 text_stream 을 버퍼에 모은 뒤 stop_reason 확인 후 flush.
        → tool_use 라운드는 버퍼를 버려 SSE 무음 처리, 최종 텍스트 라운드만 클라이언트에 전송.
        Redis 히스토리에는 사용자 텍스트 ↔ 어시스턴트 최종 텍스트만 저장.
        """
        location = self._get_location(user_id, lat, lon)
        system_prompt = self._build_system_prompt(location)
        history = self.get_history(user_id)

        working_messages: list[dict] = history[-_MAX_HISTORY:] + [
            {"role": "user", "content": content}
        ]

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        final_text = ""

        for _round in range(_MAX_TOOL_ROUNDS):
            round_buffer: list[str] = []

            with client.messages.stream(
                model=self.settings.anthropic_model,
                max_tokens=4096,
                system=system_prompt,
                messages=working_messages,
                tools=_CHAT_TOOLS,
                thinking={"type": "adaptive"},
            ) as stream:
                # stop_reason 을 알기 전이므로 버퍼에만 수집
                for text_chunk in stream.text_stream:
                    round_buffer.append(text_chunk)
                final_msg = stream.get_final_message()

            if final_msg.stop_reason != "tool_use":
                # 최종 텍스트 라운드 — 버퍼를 SSE로 flush
                for chunk in round_buffer:
                    final_text += chunk
                    yield json.dumps({"text": chunk, "done": False}, ensure_ascii=False)
                break

            # 도구 호출 라운드 — 버퍼 무시(SSE 무음), 도구 실행
            serialized_content = _serialize_content(final_msg.content)
            tool_results = []
            for block in final_msg.content:
                if block.type == "tool_use":
                    tool_result = self._execute_tool(block.name, block.input, user_id, location)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result,
                    })

            working_messages.append({"role": "assistant", "content": serialized_content})
            working_messages.append({"role": "user", "content": tool_results})

        # Redis 히스토리: tool_use 중간 턴 제외, 사용자 텍스트 + 최종 답변만 저장
        self._save_history(user_id, history + [
            {"role": "user", "content": content},
            {"role": "assistant", "content": final_text},
        ])

        yield json.dumps({"text": "", "done": True}, ensure_ascii=False)
