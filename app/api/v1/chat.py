from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.chat import ChatHistoryMessage, ChatHistoryResponse, ChatMessageRequest
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_session),
) -> ChatService:
    return ChatService(redis=redis, settings=settings, db=db)


@router.post("/message")
def send_message(
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """FUNC-005: 채팅 메시지 전송 — Claude AI 응답을 SSE 스트림으로 반환.

    응답 형식 (text/event-stream):
      data: {"text": "...", "done": false}  ← 중간 청크
      data: {"text": "", "done": true}       ← 완료 신호

    대화 이력은 Redis에 최대 20개 메시지 / 24시간 TTL로 보관된다.
    """
    def event_stream():
        for chunk in service.stream_message(
            current_user.user_id, body.content, lat=body.lat, lon=body.lon
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history", response_model=ChatHistoryResponse)
def get_history(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    """FUNC-005: 대화 이력 조회 (앱 재시작 시 복원용)."""
    messages = service.get_history(current_user.user_id)
    return ChatHistoryResponse(
        messages=[ChatHistoryMessage(**m) for m in messages]
    )


