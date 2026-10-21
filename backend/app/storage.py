"""轻量 JSON 文件存储。

用途：
- 生成的试卷（供 MD 下载、预览）
- 上传解析后的题库（隐藏标准答案，服务端留档用于阅卷）
- 阅卷结果（供错题 MD 下载）

特点：线程锁 + 原子写 + TTL 过期清理，无需额外数据库即可完整运行。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class JsonStore:
    """以 JSON 文件保存短期业务数据。"""

    def __init__(self, root: Path, ttl_hours: int) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(1, int(ttl_hours * 3600))
        self._lock = threading.Lock()
        self._last_cleanup = 0.0

    def _path(self, key: str) -> Path:
        if not _KEY_PATTERN.match(key):
            raise ValueError(f"非法的存储 key: {key!r}")
        return self.root / f"{key}.json"

    def save(self, key: str, payload: dict[str, Any]) -> None:
        """原子写入，附带 _stored_at 时间戳。"""
        path = self._path(key)
        record = dict(payload)
        record["_stored_at"] = time.time()
        data = json.dumps(record, ensure_ascii=False, separators=(",", ":"))

        with self._lock:
            fd, tmp_name = tempfile.mkstemp(prefix=f".{key}.", suffix=".tmp", dir=str(self.root))
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(data)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_name, path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)

            # 每 10 分钟清理一次过期文件
            now = time.time()
            if now - self._last_cleanup > 600:
                self._last_cleanup = now
                self._cleanup_locked(now)

    def load(self, key: str) -> dict[str, Any] | None:
        """读取并校验 TTL；不存在 / 已过期返回 None。"""
        if not _KEY_PATTERN.match(key):
            return None
        path = self._path(key)
        if not path.exists():
            return None

        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        stored_at = float(record.get("_stored_at", 0))
        if time.time() - stored_at > self.ttl_seconds:
            self.delete(key)
            return None
        return record

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except (OSError, ValueError):
            pass

    def _cleanup_locked(self, now: float) -> None:
        for path in self.root.glob("*.json"):
            try:
                if now - path.stat().st_mtime > self.ttl_seconds:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    def stats(self) -> dict[str, Any]:
        files = list(self.root.glob("*.json"))
        return {"files": len(files), "ttl_hours": round(self.ttl_seconds / 3600, 2)}


def build_stores(data_dir: Path, *, exam_ttl: int, paper_ttl: int, result_ttl: int) -> tuple[JsonStore, JsonStore, JsonStore]:
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    return (
        JsonStore(base / "exams", exam_ttl),
        JsonStore(base / "papers", paper_ttl),
        JsonStore(base / "results", result_ttl),
    )
