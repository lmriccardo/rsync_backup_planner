import pytest
from pathlib import Path
from backupctl import constants

@pytest.fixture(autouse=True)
def temp_backup_dirs(tmp_path: Path, monkeypatch) -> Path:
    """Redirect default backup paths into a temp folder for tests."""
    root = tmp_path / "backups"
    monkeypatch.setattr(constants, "DEFAULT_BACKUP_FOLDER", root)
    monkeypatch.setattr(constants, "DEFAULT_EXCLUDE_FOLDER", root / "rsync-exclude")
    monkeypatch.setattr(constants, "DEFAULT_LOG_FOLDER", root / "log")
    monkeypatch.setattr(constants, "DEFAULT_PLAN_CONF_FOLDER", root / "plans")
    monkeypatch.setattr(constants, "REGISTERED_JOBS_FILE", root / "REGISTRY")
    return root
