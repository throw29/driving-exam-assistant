"""试卷生成、预览与 Markdown 下载接口。"""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from ..models import ExamGenerateRequest
from ..responses import ok
from ..services import bank, exam_service
from ..utils import content_disposition

router = APIRouter(tags=["试卷"])


@router.get("/exams/meta", summary="获取试卷生成可选参数（科目 / 题型 / 章节 / 题库量）")
async def exam_meta() -> dict:
    return ok(bank.build_meta(), msg="获取成功")


@router.post("/exams/generate", summary="一键生成驾考模拟试卷")
async def generate_exam(payload: ExamGenerateRequest) -> dict:
    exam = exam_service.create_exam(payload)
    return ok(exam, msg="试卷生成成功")


@router.get("/exams/{exam_id}", summary="查询已生成试卷详情（不含 Markdown）")
async def get_exam(exam_id: str) -> dict:
    return ok(exam_service.get_exam_detail(exam_id), msg="获取成功")


@router.get("/exams/{exam_id}/preview", summary="Markdown 排版预览（Markdown + HTML）")
async def preview_exam(exam_id: str) -> dict:
    return ok(exam_service.get_exam_markdown_preview(exam_id), msg="预览生成成功")


@router.get("/exams/{exam_id}/download", summary="下载 Markdown 试卷（浏览器文件流）")
async def download_exam(
    exam_id: str,
    include_answers: bool = Query(
        default=True,
        description="是否包含标准答案与解析；false 时下载空白卷",
    ),
) -> Response:
    _exam, markdown_text, display_name, ascii_name = exam_service.get_exam_markdown(
        exam_id, include_answers=include_answers
    )
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
