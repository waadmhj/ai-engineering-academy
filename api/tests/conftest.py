import os
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
os.environ["DATABASE_URL"] = "sqlite:///" + (API_DIR / "test.db").as_posix()
os.environ["AUTH_MODE"] = "local"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c
    engine.dispose()
    (API_DIR / "test.db").unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        (API_DIR / f"test.db{suffix}").unlink(missing_ok=True)
