"""共享依赖：JSON 存储实例。"""

from __future__ import annotations

from .config import settings
from .storage import build_stores

exam_store, paper_store, result_store = build_stores(
    settings.data_dir,
    exam_ttl=settings.exam_ttl_hours,
    paper_ttl=settings.paper_ttl_hours,
    result_ttl=settings.result_ttl_hours,
)
