from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """FUNC-005: 채팅 메시지 전송 요청."""

    content: str = Field(min_length=1, max_length=2000)


class ChatHistoryMessage(BaseModel):
    """대화 이력 단건."""

    role: str  # "user" | "assistant"
    content: str


class ChatHistoryResponse(BaseModel):
    """FUNC-005: 대화 이력 조회 응답."""

    messages: list[ChatHistoryMessage]
