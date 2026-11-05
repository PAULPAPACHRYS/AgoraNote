"""Test setup: a separate `agoranote_test` database, files in a temp dir, Celery tasks run inline.

Run with: docker compose run --rm api pytest
"""
import os
import tempfile

# Point the app at the test database BEFORE any app module reads the config.
_dev_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://agoranote:agoranote@db:5432/agoranote")
_base, _dev_db = _dev_url.rsplit("/", 1)
os.environ["DATABASE_URL"] = f"{_base}/agoranote_test"
os.environ["LOCAL_STORAGE_DIR"] = tempfile.mkdtemp(prefix="agoranote-test-")
os.environ["LLM_PROVIDER"] = "mock"
os.environ["TRANSCRIBE_PROVIDER"] = "mock"
os.environ["AUTH_MODE"] = "dev"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import config  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.worker import celery  # noqa: E402

# Run tasks inside .delay() instead of sending them to Redis, and let their errors reach the test.
celery.conf.task_always_eager = True
celery.conf.task_eager_propagates = True


def _create_test_database():
    """CREATE DATABASE agoranote_test once (it can't run inside a transaction, hence AUTOCOMMIT)."""
    admin = create_engine(f"{_base}/{_dev_db}", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = 'agoranote_test'"))
        if not exists:
            conn.execute(text("CREATE DATABASE agoranote_test"))
    admin.dispose()


# Fixtures are pytest's setup helpers: a test names a fixture as a parameter (e.g. `client`) and gets
# its value. autouse=True fixtures run for every test without being named; scope="session" ones only
# once per test run.
@pytest.fixture(scope="session", autouse=True)
def database():
    """Create the test database once, with tables matching the current models."""
    assert config.DATABASE_URL.endswith("/agoranote_test"), "tests must never touch the dev database"
    _create_test_database()
    Base.metadata.drop_all(engine)  # start from the current schema every run
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    """Every test starts with empty tables."""
    yield
    names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    """A test HTTP client that calls the FastAPI app directly (no real server or network needed)."""
    with TestClient(app) as c:
        yield c
