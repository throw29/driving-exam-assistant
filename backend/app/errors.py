"""业务异常定义。

所有业务异常都会被全局异常处理器转换为统一 JSON：
    {"code": 4xxx, "msg": "...", "data": ...}
HTTP 状态码与业务 code 分离：
- HTTP 401 + code 401：API-KEY 缺失或无效
- HTTP 404 + code 4040：试卷 / 题库 / 阅卷结果不存在或已过期
- HTTP 400 + code 4001：业务参数不满足（如题库数量不足）
- HTTP 422 + code 422：请求体参数校验失败
"""

from __future__ import annotations

from typing import Any


class BusinessError(Exception):
    """可预期的业务错误，直接返回给调用方。"""

    def __init__(
        self,
        code: int,
        msg: str,
        *,
        status_code: int = 400,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg
        self.status_code = status_code
        self.data = data
        self.headers = headers or {}


class ApiKeyError(BusinessError):
    """API-KEY 校验失败（对齐 Claude Code：401 + WWW-Authenticate）。"""

    def __init__(self, msg: str) -> None:
        super().__init__(
            401,
            msg,
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="driving-exam-assistant"'},
        )
