"""系统接口：健康检查。"""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..config import settings
from ..deps import exam_store, paper_store, result_store
from ..responses import ok
from ..services import bank
from ..utils import format_datetime

router = APIRouter(tags=["系统"])


@router.get("/health", summary="健康检查（同时校验 API-KEY）")
async def health(request: Request) -> dict:
    return ok(
        {
            "status": "ok",
            "name": settings.app_name,
            "version": settings.app_version,
            "time": format_datetime(),
            "timezone": settings.timezone,
            "auth": "verified",
            "key_tail": getattr(request.state, "api_key_tail", "****"),
            "bank": {
                "subjects": 2,
                "questions": len(bank.load_bank()["questions"]),
            },
            "storage": {
                "exams": exam_store.stats(),
                "papers": paper_store.stats(),
                "results": result_store.stats(),
            },
        },
        msg="服务正常",
    )
