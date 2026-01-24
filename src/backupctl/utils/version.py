import re
import subprocess
from importlib import metadata
from pathlib import Path
from typing import Optional


def _parse_version_parts(version: str) -> Optional[tuple[int, ...]]:
    parts = re.findall(r"\d+", version)
    if not parts:
        return None
    return tuple(int(p) for p in parts)


def _read_pyproject_version() -> Optional[str]:
    try:
        import tomllib
    except ModuleNotFoundError:
        return None
    root = Path(__file__).resolve().parents[3]
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data.get("project", {}).get("version")


def _read_git_latest_tag() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=version:refname"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not tags:
        return None
    return tags[-1]


def get_current_version() -> str:
    try:
        return metadata.version("backupctl")
    except metadata.PackageNotFoundError:
        pass
    version = _read_pyproject_version()
    if version:
        return version
    return _read_git_latest_tag() or "unknown"


def get_latest_version() -> Optional[str]:
    return _read_git_latest_tag()


def has_newer_version(current: str, latest: str) -> bool:
    current_parts = _parse_version_parts(current)
    latest_parts = _parse_version_parts(latest)
    if current_parts is None or latest_parts is None:
        return False
    return latest_parts > current_parts


def format_version_output() -> str:
    current = get_current_version()
    latest = get_latest_version()
    lines = [f"BACKUPCTL Version {current}"]
    if latest and has_newer_version(current, latest):
        lines.append(f"Newer version available: {latest}")
    return "\n".join(lines)
