from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from backupctl.constants import (
    DEFAULT_PLAN_CONF_FOLDER,
    DEFAULT_PLAN_SUFFIX,
    REGISTERED_JOBS_FILE,
)
from backupctl.models.plan_config import PlanCfg, load_plan_configuration
from backupctl.models.registry import Job, JobStatusType, Registry, read_registry
from backupctl.utils.exceptions import InputValidationError, ensure


@dataclass
class InspectInfo:
    name: str
    status: JobStatusType
    log_path: Path
    schedule: str
    last_run: str
    exit_code: str
    exit_code_source: str
    command: str


def _human_schedule(cmd: str) -> str:
    parts = cmd.split()
    if len(parts) < 6:
        return "unknown"
    return " ".join(parts[:5])


def _find_latest_log(log_dir: Path) -> Optional[Path]:
    if not log_dir.exists() or not log_dir.is_dir():
        return None
    candidates = [p for p in log_dir.iterdir() if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _parse_log_meta(log_path: Path) -> tuple[str, str]:
    last_run = "unknown"
    exit_code = "unknown"
    try:
        with log_path.open("r", encoding="utf-8") as io:
            for line in io:
                line = line.strip()
                if line.startswith("Started :"):
                    last_run = line.split(":", 1)[1].strip()
                elif line.startswith("Exit code:"):
                    exit_code = line.split(":", 1)[1].strip()
    except OSError:
        return last_run, exit_code
    return last_run, exit_code


def _load_plan(target_name: str) -> PlanCfg:
    plan_path = DEFAULT_PLAN_CONF_FOLDER / f"{target_name}{DEFAULT_PLAN_SUFFIX}"
    if not plan_path.exists():
        raise InputValidationError(f"Plan file not found for target '{target_name}'")
    try:
        return load_plan_configuration(plan_path)
    except ValueError as exc:
        raise InputValidationError(str(exc)) from exc


def _inspect_target(job: Job) -> InspectInfo:
    plan = _load_plan(job.name)
    log_path = Path(plan.log)
    schedule = _human_schedule(job.cmd)
    command = " ".join(plan.command) if isinstance(plan.command, list) else str(plan.command)
    last_run = "unknown"
    exit_code = "unknown"
    exit_code_source = "unknown"

    latest_log = _find_latest_log(log_path)
    if latest_log:
        last_run, exit_code = _parse_log_meta(latest_log)
        exit_code_source = str(latest_log)

    return InspectInfo(
        name=job.name,
        status=job.status,
        log_path=log_path,
        schedule=schedule,
        last_run=last_run,
        exit_code=exit_code,
        exit_code_source=exit_code_source,
        command=command,
    )


def _format_status(status: JobStatusType) -> str:
    mark = "✅" if status == JobStatusType.enabled else "❌"
    return f"{status.value.lower()} {mark}"


def _format_block(info: InspectInfo) -> str:
    return "\n".join(
        [
            f"Name      : {info.name}",
            f"Status    : {_format_status(info.status)}",
            f"Log Path  : {info.log_path}",
            f"Schedule  : {info.schedule}",
            f"Last Run  : {info.last_run}",
            f"Exit Code : {info.exit_code} ({info.exit_code_source})",
            f"Command   : {info.command}",
        ]
    )


def _get_registry() -> Registry:
    if not REGISTERED_JOBS_FILE.exists():
        raise InputValidationError("Registry file not found")
    registry = read_registry()
    if not registry:
        raise InputValidationError("Registry is empty")
    return registry


def inspect_targets(targets: Optional[List[str]]) -> List[str]:
    registry = _get_registry()
    selected: Iterable[Job]
    if targets:
        missing = [t for t in targets if t not in registry]
        ensure(not missing, f"Targets not found: {', '.join(missing)}", InputValidationError)
        selected = [registry[t] for t in targets]
    else:
        selected = registry.values()

    blocks = [_format_block(_inspect_target(job)) for job in selected]
    return blocks
