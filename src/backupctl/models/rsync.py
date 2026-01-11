import ipaddress

from typing import Optional, List, Annotated
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from subprocess import CompletedProcess
from pydantic import (
    BaseModel, ConfigDict, Field, AfterValidator, 
    field_validator, model_validator,
)

class CaseInsensitiveEnum(str, Enum):
    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str): return None
        for member in cls:
            if member.value.lower() == value.lower():
                return member

class DeleteType(CaseInsensitiveEnum):
    delete_after    = "after"
    delete_before   = "before"
    delete_delay    = "delay"
    delete_during   = "during"
    delete_excluded = "excluded"

class RSyncStatus(str, Enum):
    OK = "ok"
    UNKNOWN_MODULE = "unknown_module"
    AUTH_FAILED = "auth_failed"
    ACCESS_DENIED = "access_denied"
    OTHER_ERROR = "other_error"
    FOLDER_NOT_FOUND = "folder_not_found"

    @staticmethod
    def from_output( ok: bool, output: str ) -> 'RSyncStatus':
        if ok: return RSyncStatus.OK
        if "@ERROR: Unknown module" in output: return RSyncStatus.UNKNOWN_MODULE
        if "@ERROR: auth failed" in output: return RSyncStatus.AUTH_FAILED
        if "@ERROR: access denied" in output: return RSyncStatus.ACCESS_DENIED
        if "No such file or directory" in output: return RSyncStatus.FOLDER_NOT_FOUND
        return RSyncStatus.OTHER_ERROR

@dataclass
class RSyncOutput:
    status : RSyncStatus # The status of the rsync command execution
    return_code : int         # The return code of the command execution
    stdout : str              # What the command printed out in the stdout
    stderr : str              # What the command printed out in the stderr

    @staticmethod
    def from_cmd_out( out: CompletedProcess ) -> 'RSyncOutput':
        """ Create an output object from the subprocess.run output """
        rsync_out = RSyncOutput(None, None, None, None)
        rsync_out.return_code = out.returncode
        rsync_out.stdout = str(out.stdout) or ""
        rsync_out.stderr = str(out.stderr) or ""
        combined = (rsync_out.stdout + "\n" + rsync_out.stderr).strip()
        ok = rsync_out.return_code == 0
        rsync_out.status = RSyncStatus.from_output(ok, combined)
        return rsync_out
    
def validate_host(v_host: str) -> str:
    # The host parameter must be non-empty and there
    # must not be spaces.
    v_host = v_host.strip()
    if not v_host: raise ValueError("Host must not be empty")
    if "://" in v_host: raise ValueError("host must not include a URL scheme")
    if "/" in v_host: raise ValueError("host must not include '/'")
    if any(c.isspace() for c in v_host): 
        raise ValueError("host must not contain spaces")

    # Accept IPv4 / IPv6
    try:
        ipaddress.ip_address(v_host.strip("[]"))
        return v_host
    except ValueError:
        pass

    for host_label in v_host.split("."):
        if not host_label: raise ValueError("invalid hostname label")
        if host_label.startswith("-") or host_label.endswith("-"):
            raise ValueError(
                f"invalid hostname label: {host_label}")

        if not host_label.replace("-", "").isalnum():
            raise ValueError(
                f"invalid hostname label: {host_label}")

    return v_host

HostField = Annotated[
    str,
    AfterValidator(validate_host),
    Field(description="IPv4, IPv6 (optionally bracketed), or hostname")
]

class RSyncOptionsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # catches typos

    host: HostField
    port: int = Field(ge=1, le=65535)

    user: Optional[str] = None
    password_file: Optional[str] = None

    list_only: bool = True
    dry_run: bool = False
    delete: Optional[DeleteType] = None
    progress: bool = False
    prune_empty_dirs: bool = True

    exclude_from: Optional[str] = None
    excludes: List[str] = Field(default_factory=list)
    includes: List[str] = Field(default_factory=list)

    numeric_ids: bool = True
    use_flags: bool = False
    itemize_changes: bool = False

    module: Optional[str] = None
    folder: Optional[str] = None
    sources: List[str] = Field(default_factory=list)

    verbose: bool = False

    @field_validator("user", "module", "folder")
    @classmethod
    def non_empty_validation(cls, v: str | None) -> str | None:
        if v is None: return None
        if not v.strip(): raise ValueError( "must be non-empty" )
        return v.strip()
        
    @field_validator("password_file", "exclude_from")
    @classmethod
    def path_must_exist(cls, path: str | None) -> str | None:
        if path is None: return None
        if not path.strip(): raise ValueError("must be non-empty")
        path = Path(path.strip()).expanduser()
        if not path.is_file(): 
            raise ValueError(f"{path} must be an existing file")
        return str(path)
    
    @model_validator(mode="after")
    def validate_user_and_password(self) -> 'RSyncOptionsModel':
        # If password_file is given and it is not None
        # then also user must be non-empty or not None.
        # The other way around does not count, a username
        # could potentially not require a password I guess
        if self.password_file is None: return self
        if self.user is None:
            raise ValueError("When password file is given, user must be non Null")
        return self
    
    @model_validator(mode="after")
    def validate_list_only_semantics(self) -> 'RSyncOptionsModel':
        # If list-only is given, then we need to restore
        # delete to its default value, as well for sources, 
        # includes and exclude.
        if self.list_only:
            self.prune_empty_dirs = False
            self.exclude_from = None
            self.includes.clear()
            self.excludes.clear()
            self.sources.clear()
            self.delete = None
            self.dry_run = False

            return self
        
        # Otherwise, if list only is False, then sources
        # and module is required.
        if not self.sources or not self.module:
            raise ValueError(
                "Both 'module' and 'sources' are required")
        
        return self
    
    @model_validator(mode="after")
    def validate_module_and_folder(self) -> 'RSyncOptionsModel':
        # If folder is given then also module must exists
        if self.folder is not None and self.module is None:
            raise ValueError("If Folder is given then also Module must be present")
        return self