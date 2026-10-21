"""统一响应体构造。"""

from __future__ import annotations

from typing import Any

SUCCESS_CODE = 0


def envelope(code: int = SUCCESS_CODE, msg: str = "success", data: Any = None) -> dict[str, Any]:
    """构造标准响应结构：code / msg / data。"""
    return {"code": code, "msg": msg, "data": data}


def ok(data: Any = None, msg: str = "success") -> dict[str, Any]:
    return envelope(SUCCESS_CODE, msg, data)


def fail(code: int, msg: str, data: Any = None) -> dict[str, Any]:
    return envelope(code, msg, data)
