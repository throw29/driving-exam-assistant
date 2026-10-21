"""自定义题库上传解析接口。"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from ..config import settings
from ..errors import BusinessError
from ..responses import ok
from ..services.parser_service import parse_question_file

router = APIRouter(tags=["题库上传"])


@router.post("/questions/upload", summary="上传 txt / md 题库文件并自动解析")
async def upload_questions(file: UploadFile = File(..., description="txt 或 md 格式题库文件")) -> dict:
    if not file.filename:
        raise BusinessError(4004, "请选择要上传的题库文件。")

    # 多读 1 字节用于判断是否超限，避免大文件占满内存
    data = await file.read(settings.max_upload_bytes + 1)
    result = parse_question_file(file.filename, data)
    return ok(result, msg="题库解析成功")
