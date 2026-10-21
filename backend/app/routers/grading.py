"""在线答题、自动阅卷与错题 Markdown 导出接口。"""

from __future__ import annotations

from fastapi import APIRouter, Response

from ..models import GradingSubmitRequest
from ..responses import ok
from ..services import grading_service
from ..utils import content_disposition

router = APIRouter(tags=["阅卷"])


@router.post("/grading/submit", summary="提交作答并自动阅卷评分")
async def submit_grading(payload: GradingSubmitRequest) -> dict:
    result = grading_service.submit_grading(
        paper_id=payload.paper_id,
        answers=payload.answers,
        duration_seconds=payload.duration_seconds,
    )
    return ok(result, msg="阅卷完成")


@router.get("/grading/{result_id}", summary="查询阅卷结果")
async def get_result(result_id: str) -> dict:
    return ok(grading_service.get_grading_result(result_id), msg="获取成功")


@router.get("/grading/{result_id}/wrong-answers/download", summary="下载错题集 Markdown 文件")
async def download_wrong_answers(result_id: str) -> Response:
    _result, markdown_text, display_name, ascii_name = grading_service.get_wrong_markdown(result_id)
    headers = {
        "Content-Disposition": content_disposition(display_name, ascii_name),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(
        content=markdown_text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )
