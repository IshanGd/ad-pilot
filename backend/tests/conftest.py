"""Test fixtures. Forces a throwaway SQLite DB before the app is imported."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="adpilot_test_")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ.pop("WASTE_COST_THRESHOLD", None)
# Never hit a real LLM from the test suite — force the template path.
os.environ["EXPLAINER_ENABLED"] = "false"
os.environ.pop("LLM_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models.db import init_db  # noqa: E402

SAMPLE_CSV = (
    Path(__file__).resolve().parents[2]
    / "sample_data"
    / "sample_google_ads_report.csv"
)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    init_db()
    yield
    try:
        os.unlink(_db_path)
    except OSError:
        pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_csv_bytes() -> bytes:
    return SAMPLE_CSV.read_bytes()
