from backupctl.constants import CRONTAB_TAG_PREFIX, \
    REGISTERED_JOBS_FILE

from typing import Dict, TypeAlias
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from collections import defaultdict

class JobStatusType(str, Enum):
    enabled  = "ENABLED"
    disabled = "DISABLED"

    @staticmethod
    def fromstr( t: str ) -> 'JobStatusType':
        if not isinstance(t, str):
            raise TypeError("status must be a string")
        
        match t.strip().upper():
            case JobStatusType.enabled.value:
                return JobStatusType.enabled
            case JobStatusType.disabled.value:
                return JobStatusType.disabled
            case _:
                raise ValueError(f"invalid job status: {t}")
            
    def __str__(self) -> str:
        return self.value

@dataclass
class Job:
    name   : str            # The name of the Job
    cmd    : str            # The cronjob command (including the time schedule)
    status : JobStatusType  # The Job status ( enabled/disabled )

    def is_enabled(self) -> bool:
        return self.status == JobStatusType.enabled
    
    def tag(self) -> str:
        """ Returns the TAG to identify this job """
        return f"{CRONTAB_TAG_PREFIX}{self.name}"
    
    def to_cron(self, with_tag: bool=False) -> str:
        """ Returns the cron line with the tag suffix if required """
        suffix = "" if not with_tag else self.tag()
        prefix = "" if self.is_enabled() else "# "
        return f"{prefix}{self.cmd} {suffix}"
    
    def __str__(self) -> str:
        return f"{self.name} {self.cmd} {self.status.value}"
    
Registry: TypeAlias = Dict[str, Job] | None

def load_registry( path: Path ) -> Registry:
    """ Load all registered jobs from the input path """
    # If the path does not exists, create it and returns empty dict
    if not path.expanduser().exists():
        path.expanduser().touch()
        return dict()
    
    with path.expanduser().open('r', encoding='utf-8') as io:
        registered_jobs = defaultdict(Job)
        while (line := io.readline()):
            name, *cmd, status = line.strip().removesuffix("\n").split()
            registered_jobs[name] = Job(name, (" ".join(cmd)).strip(), 
                JobStatusType.fromstr(status))
        
        return registered_jobs
    
def write_registry( path: Path, registry: Registry ) -> None:
    """ Write the registry into the input path """
    from backupctl.utils.exceptions import RegistryError
    try:
        path = path.expanduser().resolve()
        if not path.exists(): path.touch()
        content = "\n".join( map(str, registry.values()) )
        path.write_text( content, encoding='utf-8' )
    except Exception as e:
        raise RegistryError(f"Registry writing: {e}") from e

def read_registry() -> Registry:
    """ Load the registry or returns None if the
    registry file does not exists. """
    if not REGISTERED_JOBS_FILE.exists():
        return None

    registry = load_registry( REGISTERED_JOBS_FILE )
    return None if len(registry) == 0 else registry
