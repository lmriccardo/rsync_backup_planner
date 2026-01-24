import subprocess


def test_cli_help() -> None:
    """Ensures main CLI help exits successfully."""
    out = subprocess.run(
        ["python", "-m", "backupctl", "-h"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0
    assert "backupctl" in out.stdout.lower()


def test_inspect_help() -> None:
    """Ensures inspect subcommand help exits successfully."""
    out = subprocess.run(
        ["python", "-m", "backupctl", "inspect", "-h"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0
