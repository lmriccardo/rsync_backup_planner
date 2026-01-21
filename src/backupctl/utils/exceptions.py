from typing import Callable, Type
from functools import wraps


class BackupCtlError(Exception):
    """Base class for expected backupctl errors."""


class InputValidationError(BackupCtlError):
    """Invalid or missing user input/configuration."""


class PermissionDeniedError(BackupCtlError):
    """Permission-related failure for filesystem operations."""


class ExternalCommandError(BackupCtlError):
    """Failure when invoking external commands (e.g. crontab)."""


class RegistryError(BackupCtlError):
    """Registry read/write errors."""

def assertion_wrapper(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except BackupCtlError as err:
            print(f"[ERROR] {err}")
            return False

    return wrapper

def ensure(condition: bool, msg: str, exc_type: Type[BackupCtlError]) -> None:
    if not condition:
        raise exc_type(msg)
