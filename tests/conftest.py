import pytest

import hq.db.models as models


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Point the DB at a temp directory and reset the singleton for every test."""
    monkeypatch.setattr(models, "HQ_DIR", tmp_path)
    monkeypatch.setattr(models, "DB_PATH", tmp_path / "hq.db")
    models._db = None
    yield
    models._db = None
