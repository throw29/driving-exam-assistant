"""pytest 公共配置：隔离测试数据目录、固定 API-KEY、提供 TestClient。"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# 必须在导入 app 之前设置，config.py 在导入时读取环境变量
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="dtk-test-data-")
os.environ["DT_API_KEY"] = "sk-dtk-test-only-123456"
os.environ["DT_DATA_DIR"] = _TEST_DATA_DIR
os.environ["DT_CORS_ORIGINS"] = "*"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

API_KEY = "sk-dtk-test-only-123456"
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


@pytest.fixture(scope="session")
def sample_markdown_bytes() -> bytes:
    return (SAMPLES_DIR / "sample_bank.md").read_bytes()


@pytest.fixture(scope="session")
def sample_text_bytes() -> bytes:
    return (SAMPLES_DIR / "sample_bank.txt").read_bytes()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_data():
    yield
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)
