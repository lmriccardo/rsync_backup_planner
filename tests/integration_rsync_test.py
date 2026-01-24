import subprocess
import textwrap
import time
from pathlib import Path

import pytest

from backupctl.validate._core import Args, validate_target
from backupctl.models.user_config import NamedTarget, Target, Remote, RemoteDest, RsyncCfg, Schedule


@pytest.mark.integration
def test_validate_against_local_rsync_daemon(tmp_path):
    rsync_root = tmp_path / "rsync"
    rsync_root.mkdir()
    (rsync_root / "data").mkdir()

    secrets = tmp_path / "secrets"
    secrets.mkdir()
    password_file = secrets / "rsync_pass"
    password_file.write_text("testpass\n", encoding="utf-8")

    rsync_conf = tmp_path / "rsyncd.conf"
    rsync_conf.write_text(
        textwrap.dedent(
            f"""
            pid file = {tmp_path / "rsyncd.pid"}
            use chroot = no
            log file = {tmp_path / "rsyncd.log"}
            [backup]
              path = {rsync_root}
              read only = false
              auth users = testuser
              secrets file = {password_file}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        ["rsync", "--daemon", "--no-detach", f"--config={rsync_conf}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.3)
        target = Target(
            remote=Remote(
                host="127.0.0.1",
                port=873,
                user="testuser",
                password_file=str(password_file),
                dest=RemoteDest(module="backup", folder="."),
            ),
            rsync=RsyncCfg(
                sources=[str(tmp_path / "src")],
            ),
            schedule=Schedule(),
            notification=None,
        )
        (tmp_path / "src").mkdir()
        args = Args(config_file=Path("dummy.yml"), verbose=False)
        validate_target(NamedTarget.from_target("sample", target), args)
    finally:
        proc.terminate()
        proc.wait(timeout=5)
