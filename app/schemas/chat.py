from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """FUNC-005: 채팅 메시지 전송 요청."""

    content: str = Field(min_length=1, max_length=2000)
    lat: float | None = None  # 현재 위치 위도 (생략 시 Redis 캐시 재사용)
    lon: float | None = None  # 현재 위치 경도


class ChatInitRequest(BaseModel):
    """FUNC-005: 채팅 초기화 요청 — 위치 기반 프로액티브 추천."""

    lat: float
    lon: float


class ChatHistoryMessage(BaseModel):
    """대화 이력 단건."""

    role: str  # "user" | "assistant"
    content: str


class ChatHistoryResponse(BaseModel):
    """FUNC-005: 대화 이력 조회 응답."""

    messages: list[ChatHistoryMessage]
