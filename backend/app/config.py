"""全局配置。

配置优先级：环境变量 / backend/.env > 代码内默认值。
所有可变项均提供默认值，保证开箱即用；生产环境请务必修改 API-KEY。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# backend/ 目录（config.py 位于 backend/app/config.py）
BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

# 读取 backend/.env（不存在时静默跳过）
load_dotenv(BACKEND_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _parse_origins(raw: str) -> tuple[str, ...]:
    items = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    return tuple(items) or ("*",)


# 预设的全局有效 API-KEY（与 Claude Code 的 API Key 校验方式对齐：
# 精确匹配、常量时间比较、支持 Authorization: Bearer 与 x-api-key 两种传递方式）
DEFAULT_API_KEY = "sk-dtk-local-2026-change-me"


@dataclass(frozen=True)
class Settings:
    """应用设置（不可变，进程启动时一次性读取）。"""

    app_name: str = "驾考宝典智能查询助手"
    app_version: str = "0.1.0"
    description: str = (
        "驾校内部业务工具：一键生成驾考模拟试卷并下载 Markdown、"
        "对话式查询驾考知识点、上传自定义题库并自动阅卷。"
    )

    host: str = os.getenv("DT_HOST", "127.0.0.1")
    port: int = _env_int("DT_PORT", 8000)
    reload: bool = _env_bool("DT_RELOAD", False)

    # 鉴权：优先读取 DT_API_KEY，其次兼容 Claude Code 常用的 ANTHROPIC_API_KEY
    api_key: str = (
        os.getenv("DT_API_KEY", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
        or DEFAULT_API_KEY
    )
    api_key_env: str = (
        "DT_API_KEY"
        if os.getenv("DT_API_KEY", "").strip()
        else ("ANTHROPIC_API_KEY" if os.getenv("ANTHROPIC_API_KEY", "").strip() else "default")
    )

    # 跨域：默认允许全部来源（内部工具、file:// 直接打开也能用）
    cors_origins: tuple[str, ...] = _parse_origins(os.getenv("DT_CORS_ORIGINS", "*"))

    # 数据目录与过期时间
    data_dir: Path = Path(os.getenv("DT_DATA_DIR", str(BACKEND_DIR / ".data"))).resolve()
    exam_ttl_hours: int = _env_int("DT_EXAM_TTL_HOURS", 24)
    paper_ttl_hours: int = _env_int("DT_PAPER_TTL_HOURS", 24)
    result_ttl_hours: int = _env_int("DT_RESULT_TTL_HOURS", 72)

    # 上传限制
    max_upload_mb: float = _env_float("DT_MAX_UPLOAD_MB", 2.0)
    max_upload_questions: int = _env_int("DT_MAX_UPLOAD_QUESTIONS", 300)

    timezone: str = os.getenv("DT_TIMEZONE", "Asia/Shanghai")

    # 业务阈值
    pass_score: int = _env_int("DT_PASS_SCORE", 90)

    @property
    def api_prefix(self) -> str:
        return "/api/v1"

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


settings = Settings()
