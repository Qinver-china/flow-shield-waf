from pathlib import Path

from app.core.config import settings
from app.services import schema_bootstrap


def test_bootstrap_lock_path_follows_db_path():
    assert schema_bootstrap._LOCK_PATH == Path(settings.db_path).with_suffix(".bootstrap.lock")
