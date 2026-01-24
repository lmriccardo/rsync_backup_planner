import subprocess
import textwrap
import socket
import time
import shutil
from pathlib import Path

import pytest

from backupctl.validate._core import Args, validate_target
from backupctl.models.user_config import (
    NamedTarget,
    Target,
    Remote,
    RemoteDest,
    RsyncCfg,
    Schedule,
    NotificationCfg,
)


@pytest.mark.integration
def test_validate_against_local_rsync_daemon(tmp_path):
    if shutil.which("rsync") is None:
        pytest.fail("rsync not installed")

    rsync_root = tmp_path / "rsync"
    rsync_root.mkdir()
    (rsync_root / "data").mkdir()

    secrets = tmp_path / "secrets"
    secrets.mkdir()
    password_file = secrets / "rsync_pass"
    password_file.write_text("testpass\n", encoding="utf-8")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    rsync_conf = tmp_path / "rsyncd.conf"
    rsync_conf.write_text(
        textwrap.dedent(
            f"""
            pid file = {tmp_path / "rsyncd.pid"}
            use chroot = no
            log file = {tmp_path / "rsyncd.log"}
            address = 127.0.0.1
            port = {port}
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
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 5.0
        while True:
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                pytest.fail(f"rsync daemon exited early: {stderr.strip()}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if time.time() > deadline:
                    stderr = proc.stderr.read() if proc.stderr else ""
                    pytest.fail(f"rsync daemon not reachable: {stderr.strip()}")
                time.sleep(0.1)
        target = Target(
            remote=Remote(
                host="127.0.0.1",
                port=port,
                user="testuser",
                password_file=str(password_file),
                dest=RemoteDest(module="backup", folder="."),
            ),
            rsync=RsyncCfg(
                sources=[str(tmp_path / "src")],
            ),
            schedule=Schedule(),
            notification=NotificationCfg(),
        )
        (tmp_path / "src").mkdir()
        args = Args(config_file=Path("dummy.yml"), verbose=False)
        validate_target(NamedTarget.from_target("sample", target), args)
    finally:
        proc.terminate()
        proc.wait(timeout=5)
