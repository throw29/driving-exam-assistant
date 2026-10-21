"""通用工具：时间、ID、文件名、Markdown 下载响应头。"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .config import settings

_SAFE_NAME = re.compile(r"[^\w\u4e00-\u9fff.\-]+", re.UNICODE)


def now_local() -> datetime:
    """返回配置时区的当前时间。

    Windows 未安装 tzdata 时自动回退到 UTC+8，保证服务可启动。
    """
    try:
        tz = ZoneInfo(settings.timezone)
    except Exception:
        try:
            tz = ZoneInfo("Asia/Shanghai")
        except Exception:
            tz = timezone(timedelta(hours=8), name="Asia/Shanghai")
    return datetime.now(tz)


def format_datetime(value: datetime | None = None) -> str:
    """格式化为 YYYY-MM-DD HH:mm:ss。"""
    value = value or now_local()
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_expiry(hours: int) -> str:
    return format_datetime(now_local() + timedelta(hours=hours))


def new_id(prefix: str) -> str:
    """生成短小、URL 安全的业务 ID：prefix_时间戳_随机串。"""
    stamp = now_local().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{stamp}_{secrets.token_hex(4)}"


def safe_filename(name: str, fallback: str = "file") -> str:
    """清理用户提供的文件名，避免路径穿越与响应头注入。"""
    base = Path(name or "").name.strip()
    base = base.replace("\r", "").replace("\n", "").replace('"', "")
    base = _SAFE_NAME.sub("_", base)
    base = re.sub(r"\.{2,}", ".", base).strip(" ")
    return base[:80] or fallback


def content_disposition(filename: str, ascii_fallback: str) -> str:
    """构造同时兼容中文与老浏览器的 Content-Disposition。"""
    quoted = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quoted}"


def human_duration(seconds: int | None) -> str:
    """将秒数转为“X 分 Y 秒”。"""
    if seconds is None:
        return "—"
    seconds = max(0, int(seconds))
    minutes, rest = divmod(seconds, 60)
    if minutes:
        return f"{minutes} 分 {rest} 秒"
    return f"{rest} 秒"


def md_escape_cell(text: str) -> str:
    """转义 Markdown 表格中的竖线与换行。"""
    return str(text).replace("|", "\\|").replace("\n", "<br>")
