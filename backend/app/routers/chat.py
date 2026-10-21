"""对话式驾考知识问答接口。"""

from __future__ import annotations

from fastapi import APIRouter

from ..models import ChatRequest
from ..responses import ok
from ..services import chat_service

router = APIRouter(tags=["问答"])


@router.get("/chat/suggestions", summary="获取热门问题、知识分类与能力介绍")
async def chat_suggestions() -> dict:
    return ok(chat_service.get_chat_suggestions(), msg="获取成功")


@router.post("/chat", summary="驾考知识点智能问答（支持多轮上下文）")
async def chat(payload: ChatRequest) -> dict:
    result = chat_service.answer_question(
        message=payload.message,
        history=payload.history,
        session_id=payload.session_id,
    )
    return ok(result, msg="回答成功")
