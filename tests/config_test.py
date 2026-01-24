import textwrap
import pytest

from backupctl.models.user_config import load_user_configuration


def _write_config(tmp_path, password_file, source_dir):
    config_path = tmp_path / "backup-plan.yml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            backup:
              targets:
                sample:
                  remote:
                    host: 127.0.0.1
                    port: 873
                    user: testuser
                    password_file: {password_file}
                    dest:
                      module: backup
                      folder: "."
                  rsync:
                    sources:
                      - {source_dir}
                  schedule:
                    minute: 0
                    hour: 3
                    day: null
                    month: null
                    weekday: null
                  notification: {{}}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


def test_load_valid_config(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("data", encoding="utf-8")
    password_file = tmp_path / ".rsync_pass"
    password_file.write_text("testpass\n", encoding="utf-8")

    config_path = _write_config(tmp_path, password_file, source_dir)
    config = load_user_configuration(config_path)

    assert config.backup.targets is not None
    assert "sample" in config.backup.targets


def test_invalid_config_rejected(tmp_path):
    config_path = tmp_path / "invalid.yml"
    config_path.write_text("backup: 123\n", encoding="utf-8")

    with pytest.raises(Exception):
        load_user_configuration(config_path)
