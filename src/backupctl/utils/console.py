from __future__ import annotations

import os
import sys
from typing import Any

try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.text import Text
except Exception:  # pragma: no cover - fallback when rich is missing
    Console = None  # type: ignore[assignment]
    Theme = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]


class _PlainConsole:
    def __init__(self, file):
        self.file = file

    def print(self, *args: Any, **kwargs: Any) -> None:
        kwargs.pop("style", None)
        kwargs.pop("highlight", None)
        kwargs.pop("emoji", None)
        kwargs.pop("markup", None)
        kwargs.pop("soft_wrap", None)
        kwargs.pop("overflow", None)
        kwargs.pop("no_wrap", None)
        end = kwargs.pop("end", "\n")
        sep = kwargs.pop("sep", " ")
        print(*args, sep=sep, end=end, file=self.file)


def _env_flag(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    val = raw.strip().lower()
    if val in {"1", "true", "yes", "on"}:
        return True
    if val in {"0", "false", "no", "off"}:
        return False
    return None


def _build_console(stderr: bool = False):
    file = sys.stderr if stderr else sys.stdout
    rich_pref = _env_flag("BACKUPCTL_RICH")
    if Console is None or rich_pref is False:
        return _PlainConsole(file)

    no_color = False
    if os.getenv("NO_COLOR") is not None:
        no_color = True
    elif rich_pref is None and not file.isatty():
        no_color = True

    theme = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "green",
            "dim": "dim",
            "emphasis": "bold",
        }
    )
    return Console(file=file, no_color=no_color, theme=theme, highlight=False)


_console_cache: dict[bool, Any] = {}


def get_console(stderr: bool = False):
    if stderr not in _console_cache:
        _console_cache[stderr] = _build_console(stderr)
    return _console_cache[stderr]


def _render_message(message: str, style: str | None) -> Any:
    if style is None or Text is None:
        return message

    rendered = Text()
    lines = message.split("\n")
    for idx, line in enumerate(lines):
        if idx > 0:
            rendered.append("\n")
        if line.strip():
            rendered.append(line, style=style)
        else:
            rendered.append(line)
    return rendered


def cprint(message: str = "", **kwargs: Any) -> None:
    flush = kwargs.pop("flush", False)
    style = kwargs.get("style")
    console = get_console()
    rendered = _render_message(message, style)
    console.print(rendered, **kwargs)
    if flush and hasattr(console, "file"):
        console.file.flush()


def cinfo(message: str, **kwargs: Any) -> None:
    cprint(message, style="info", **kwargs)


def cwarn(message: str, **kwargs: Any) -> None:
    cprint(message, style="warning", **kwargs)


def cerror(message: str, **kwargs: Any) -> None:
    cprint(message, style="error", **kwargs)


def csuccess(message: str, **kwargs: Any) -> None:
    cprint(message, style="success", **kwargs)


def cdim(message: str, **kwargs: Any) -> None:
    cprint(message, style="dim", **kwargs)


def cemphasis(message: str, **kwargs: Any) -> None:
    cprint(message, style="emphasis", **kwargs)
