"""FastAPI 应用入口。

启动：
    cd backend
    uv run serve
或：
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .errors import BusinessError
from .responses import fail
from .routers import chat, exams, grading, questions, system
from .security import require_api_key
from .services import bank, chat_service

logger = logging.getLogger("driving_exam")

OPENAPI_TAGS = [
    {"name": "系统", "description": "健康检查与鉴权验证"},
    {"name": "试卷", "description": "题库元信息、一键组卷、Markdown 预览与下载"},
    {"name": "问答", "description": "驾考知识点检索问答（支持多轮上下文）"},
    {"name": "题库上传", "description": "上传 txt / md 自定义题库并解析"},
    {"name": "阅卷", "description": "在线作答提交、自动评分、错题 Markdown 导出"},
]

# 仅用于 OpenAPI 文档展示 Authorize 按钮；实际校验由 require_api_key 完成
api_key_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="APIKeyAuth",
    description="在 Swagger 右上角 Authorize 中填入 API-KEY（无需输入 Bearer 前缀）。",
)


def _uses_default_key() -> bool:
    from .config import DEFAULT_API_KEY

    return settings.api_key == DEFAULT_API_KEY


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # 启动时预热题库与知识库，数据损坏时快速失败
    bank_data = bank.load_bank()
    kb_data = chat_service.load_knowledge_base()
    logger.info(
        "服务启动：%s v%s；题库 %s 题、知识点 %s 条；API-KEY 来源=%s",
        settings.app_name,
        settings.app_version,
        len(bank_data["questions"]),
        len(kb_data["entries"]),
        settings.api_key_env,
    )
    if _uses_default_key():
        logger.warning(
            "当前使用内置默认 API-KEY，仅供本地演示；部署前请复制 .env.example 为 .env 并修改 DT_API_KEY。"
        )
    yield
    logger.info("服务已停止")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name + " API",
        version=settings.app_version,
        description=(
            settings.description
            + "\n\n### 鉴权说明\n"
            "所有 `/api/v1` 接口均需在请求头携带 API-KEY：\n\n"
            "- `Authorization: Bearer <API_KEY>`\n"
            "- 或 `x-api-key: <API_KEY>`\n\n"
            "缺失或错误统一返回 HTTP 401，响应体为 `{code, msg, data}` 标准格式。"
        ),
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---------- CORS 跨域（前后端分离，默认允许全部来源；生产可通过 DT_CORS_ORIGINS 收紧） ----------
    allow_origins = list(settings.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,  # API-KEY 放在请求头，不使用 Cookie，无需 credentials
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "Accept", "Origin"],
        expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
        max_age=86400,
    )

    # ---------- 所有业务路由统一挂载 API-KEY 依赖（无任何免鉴权业务接口） ----------
    api_router = APIRouter(
        prefix=settings.api_prefix,
        dependencies=[
            Security(api_key_scheme),
            Depends(require_api_key),
        ],
    )
    api_router.include_router(system.router)
    api_router.include_router(exams.router)
    api_router.include_router(chat.router)
    api_router.include_router(questions.router)
    api_router.include_router(grading.router)
    app.include_router(api_router)

    # ---------- 全局异常捕获：所有 JSON 接口统一 code / msg / data ----------
    @app.exception_handler(BusinessError)
    async def handle_business_error(_request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(exc.code, exc.msg, exc.data),
            headers=exc.headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for item in exc.errors():
            location = ".".join(str(part) for part in item.get("loc", []))
            errors.append(
                {
                    "field": location,
                    "message": item.get("msg", "参数不合法"),
                    "type": item.get("type", "value_error"),
                }
            )
        first = errors[0]["message"] if errors else "参数不合法"
        return JSONResponse(
            status_code=422,
            content=fail(422, f"请求参数校验失败：{first}", {"errors": errors}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status_messages = {
            401: "未授权：API-KEY 校验失败",
            403: "禁止访问",
            404: "接口不存在，请检查请求地址",
            405: "请求方法不允许",
            413: "请求体过大",
            429: "请求过于频繁，请稍后再试",
        }
        message = status_messages.get(exc.status_code) or str(exc.detail or "请求失败")
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(exc.status_code, message, None),
            headers=exc.headers or None,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未捕获异常：%s", exc)
        return JSONResponse(
            status_code=500,
            content=fail(500, "服务器内部错误，请稍后重试。", None),
        )

    return app


app = create_app()


def run() -> None:
    """控制台入口：uv run serve。"""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )
