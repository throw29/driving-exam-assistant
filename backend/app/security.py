"""API-KEY 鉴权。

校验规则对齐 Claude Code / Anthropic 官方客户端的 API Key 使用方式：

1. 请求头二选一（同时存在时以 Authorization 为准）：
   - Authorization: Bearer <API_KEY>
   - x-api-key: <API_KEY>
2. API-KEY 与后端配置的全局 key 必须完全一致；
3. 使用 hmac.compare_digest 常量时间比较，避免时序攻击；
4. 缺失 / 格式错误 / 不匹配统一返回 401，并带 WWW-Authenticate 响应头；
5. 所有 /api/v1 业务接口统一挂载本依赖，无任何免鉴权业务接口。
"""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, Request

from .config import settings
from .errors import ApiKeyError


def _normalize_bearer(value: str | None) -> str | None:
    """解析 Authorization 头，仅接受 Bearer 方案（大小写不敏感）。"""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    parts = raw.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    key = parts[1].strip()
    return key or None


def extract_api_key(
    authorization: str | None,
    x_api_key: str | None,
) -> str | None:
    """按 Claude Code 的优先级提取 API-KEY。"""
    return _normalize_bearer(authorization) or (x_api_key.strip() if x_api_key else None)


async def require_api_key(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """FastAPI 依赖：校验 API-KEY，失败抛 ApiKeyError(401)。"""
    provided = extract_api_key(authorization, x_api_key)

    if not provided:
        raise ApiKeyError(
            "缺少 API-KEY。请在请求头携带 Authorization: Bearer <API_KEY> "
            "或 x-api-key: <API_KEY>。"
        )

    if not hmac.compare_digest(provided.encode("utf-8"), settings.api_key.encode("utf-8")):
        raise ApiKeyError("API-KEY 无效，无权访问该接口。")

    # 供日志 / 审计使用（只暴露脱敏后的尾号，绝不回传完整 key）
    request.state.api_key_tail = provided[-4:]
    return provided
