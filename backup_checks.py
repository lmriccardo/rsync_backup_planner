import subprocess
import socket
import pwd
import grp
import os
import stat

from typing import Callable, Optional, NamedTuple
from backup_models import *
from dataclasses import dataclass
from functools import wraps
from enum import Enum
from collections import defaultdict

class RSyncCheckStatus(str, Enum):
    OK = "ok"
    UNKNOWN_MODULE = "unknown_module"
    AUTH_FAILED = "auth_failed"
    ACCESS_DENIED = "access_denied"
    OTHER_ERROR = "other_error"
    FOLDER_NOT_FOUND = "folder_not_found"

class UserStat(NamedTuple):
    """ User Id and Group Id of the user """
    uid: int    # The User Id
    name: str   # The name of the user
    gid: int    # The Group Id of the user
    gname: str  # The Group name of the user

class FolderStat(NamedTuple):
    """ Collection of folder stat """
    path:  Path # The folder absolute path
    owner: UserStat # Stat of the folder owner
    perms: str # String description of the permissions
    mode: int # Octet description of the permissions

def get_user_stat( folder: Optional[Path] = None ) -> UserStat:
    uid, gid = os.getuid(), os.getgid()
    if folder is not None:
        stat = folder.stat()
        uid, gid = stat.st_uid, stat.st_gid

    username = pwd.getpwuid(uid).pw_name
    groupname = grp.getgrgid(gid).gr_name
    return UserStat( uid, username, gid, groupname )

def get_folder_stat( path: str | Path ) -> FolderStat:
    folder_path = (Path(path) if isinstance(path, str) else path).absolute()
    folder_stat = folder_path.stat()
    folder_mode = oct(stat.S_IMODE(folder_stat.st_mode))
    return FolderStat( folder_path, get_user_stat(folder_path), 
        stat.filemode(folder_stat.st_mode), folder_mode)

@dataclass(frozen=True)
class Args:
    config_file: Path # The configuration file for the plan
    verbose: bool # Enable/Disable Verbosity

def assertion_wrapper(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AssertionError as ae:
            print(f"[ASSERTION] {ae}")
            return False

    return wrapper

def assert_1( condition: bool, msg: str ) -> None:
    if not condition:
        raise AssertionError( msg )
    
def print_permission_error( path: Path, with_parent: bool=False ):
    print(f"[ERORR] Permission Error when accessing/creating {path}: ")
    f_stat = get_folder_stat( path if not with_parent else path.parent )
    u_stat = get_user_stat()

    print("[ERORR] Target directory:")
    print(f"    Path       : {f_stat.path}")
    print(f"    Owner      : {f_stat.owner.name} (uid={f_stat.owner.uid})")
    print(f"    Group      : {f_stat.owner.gname} (gid={f_stat.owner.gid})")
    print(f"    Permissions: {f_stat.perms} ({f_stat.mode})")

    print()
    print("[ERROR] Current user:")
    print(f"    User       : {u_stat.name} (uid={u_stat.uid})")
    print(f"    Group      : {u_stat.gname} (gid={u_stat.gid})")

def check_user_create_in_dir( path: Path ) -> None:
    """ Checks if the current user can access the parent path of either
    the input folder or file the user would like to create/excute/read
    """
    path = path.resolve()
    if not os.access(path.parent, os.W_OK | os.X_OK):
        print_permission_error( path, with_parent=True )
        raise PermissionError("Permission error")

def check_user_can_read_in_dir( path: Path ) -> None:
    """ Check if the current user has read permissions on the folder/file """
    path = path.resolve()
    if not os.access(path.parent, os.R_OK):
        print_permission_error( path )
        raise PermissionError("Permission error")

def check_sock_connection( remote: Remote, args: Args ) -> bool:
    """ Checks the remote connection to the rsync server """
    remote_ip = socket.gethostbyname(remote.host)

    if args.verbose:
        print((
            "  ( ) Checking connection to " + 
            f"{remote.host} ({remote_ip}) on {remote.port}"
        ), end="")
    
    result = False

    try:
        with socket.create_connection((remote_ip, remote.port), timeout=2.0):
            result = True
    except OSError:
        ...

    if args.verbose:
        result_str = "OK" if result else "NO"
        print((
            f"\r  ({result_str}) Checking connection to " + 
            f"{remote.host} ({remote_ip}) on {remote.port}"
        ))

    return result

def create_rsync_command(
    host: str,
    port: int,
    user: Optional[str] = None,
    password_file: Optional[str] = None,
    list_only: bool = True,
    dry_run: bool = False,
    delete: bool = False,
    progress: bool = False,
    prune_empty_dirs: bool = True,
    exclude_from: Optional[str] = None,
    excludes: List[str] = [],
    includes: List[str] = [],
    numeric_ids: bool=True,
    use_flags: bool=False,
    module: Optional[str] = None,
    folder: Optional[str] = None,
    sources: List[str] = [],
    verbose: bool=False
) -> List[str]:
    command = ["rsync"]

    if not module and folder is not None:
        raise ValueError("If Folder is given then also Module must be present")
    
    if use_flags: command += ["-avvHAX"] if verbose else ["-aHAX"]
    if list_only: command += ["--list-only"]
    if password_file: command += [f"--password-file={password_file}"]
    if dry_run: command += ["--dry-run"]
    if delete: command += ["--delete"]
    if progress: command += ["--info=progress2"]
    if prune_empty_dirs: command += ["--prune-empty-dirs"]
    if len(includes) > 0:
        for include in includes:
            command += [f"--include={include}"]
    
    if len(excludes) > 0:
        for exclude in excludes:
            command += [f"--exclude={exclude}"]

    if exclude_from: command += [f"--exclude-from={exclude_from}"]
    if numeric_ids: command += ["--numeric-ids"]

    # Add the sources
    if sources: command.extend(sources)

    # Add the host, port, user, module and folder
    rsync_user = "" if not user else f"{user}@"
    rsync_host = f"rsync://{rsync_user}{host}:{port}/"
    if module: rsync_host += f"{module}/"
    if folder: rsync_host += f"{folder}/"
    command += [rsync_host]

    return command

def _check_rsync_module_auth( remote: Remote ) -> RSyncCheckStatus:
    """ Checks authentication to the remote rsync host and if the module exists """
    # First check that the password_file exists
    if remote.password_file is not None:
        assert_1(Path(remote.password_file).absolute().is_file(),
            f"Password file {remote.password_file} does not exists")

    password_file = None if not remote.password_file else \
        Path(remote.password_file).absolute().__str__()    
    
    command = create_rsync_command(
        remote.host, 
        remote.port,
        user=remote.user,
        password_file=password_file,
        list_only=True,
        prune_empty_dirs=False,
        numeric_ids=False,
        module=remote.dest.module,
        folder=remote.dest.folder
    )
    
    out = subprocess.run(command, capture_output=True, check=False)
    return_code = out.returncode
    result = return_code == 0

    stdout = str(out.stdout) or ""
    stderr = str(out.stderr) or ""
    combined = (stdout + "\n" + stderr).strip()

    if result: return RSyncCheckStatus.OK
    if "@ERROR: Unknown module" in combined: return RSyncCheckStatus.UNKNOWN_MODULE
    if "@ERROR: auth failed" in combined: return RSyncCheckStatus.AUTH_FAILED
    if "@ERROR: access denied" in combined: return RSyncCheckStatus.ACCESS_DENIED
    if "No such file or directory" in combined: return RSyncCheckStatus.FOLDER_NOT_FOUND
    return RSyncCheckStatus.OTHER_ERROR

def check_remote_module_auth( remote: Remote, args: Args ) -> None:
    """ Checks remote authentication with the remote rsync host """
    status = _check_rsync_module_auth( remote )

    if args.verbose:
        print("  [--] Remote module and folder authentication")
        
        # Module exists
        inner_result = status != RSyncCheckStatus.UNKNOWN_MODULE
        result_str = "OK" if inner_result else "NO"

        print(f"    ({result_str}) Checking for remote module: {remote.dest.module}")
        assert_1(inner_result, "Destination Module not found")

        # Authentication check
        inner_result = status != RSyncCheckStatus.AUTH_FAILED
        result_str = "OK" if inner_result else "NO"
        password_file = "<empty>"
        if remote.password_file:
            password_file=Path(remote.password_file).absolute().__str__()
        
        print((
            f"    ({result_str}) Checking auth with username " +
            ("<empty>" if not remote.user else remote.user) +
            f" and password file {password_file}"
        ))
        assert_1(inner_result, "Authentication failed")

        # Folder check
        inner_result = status != RSyncCheckStatus.FOLDER_NOT_FOUND
        result_str = "OK" if inner_result else "NO"
        print(f"    ({result_str}) Checking for remote folder: {remote.dest.module}/{remote.dest.folder}")
        assert_1(inner_result, "Destination Folder not found")

def check_remote_dest(remote: Remote, args: Args) -> bool:
    """ Checks if the remote destination exists """
    assert_1(check_sock_connection( remote, args ), "Connection to remote failed")
    check_remote_module_auth( remote, args )

def check_exclude_file( rsync: RsyncCfg, args: Args ) -> bool:
    """ Checks if the exclude file if given exists in the filesystem """
    if not rsync.exclude_from: return True
    if args.verbose: print("  ( ) Checking existence of {rsync.exclude_from}", end="")
    result = Path(rsync.exclude_from).absolute().is_file()
    result_str = "OK" if result else "NO"
    if args.verbose: 
        print(f"\r  ({result_str}) Checking existence of {rsync.exclude_from}")
    return result

def check_rsync_source_folders( rsync: RsyncCfg, args: Args ) -> None:
    """ Checks if all source folders exists in the current filesystem """
    if args.verbose:
        print("  [--] Checking existence and readability of all source folders in the configuration")
    
    for source_folder in rsync.sources:
        source_folder_path = Path( source_folder ).resolve()
        can_read = os.access(source_folder_path, os.R_OK)
        result = source_folder_path.exists() and can_read
        result_str = "OK" if result else "NO"

        if args.verbose:
            print(f"    ({result_str}) Checking source folder {source_folder_path}")
            if not can_read:
                print()
                print_permission_error( source_folder_path )
                print()

        assert_1(result, f"Source folder {source_folder_path} does " + \
            "not exists or cannot be read!")
        
def check_email_notification_system( email_ntify: EmailCfg, args: Args ) -> Optional[str]:
    """ Check if authentication works """
    import smtplib, ssl
    ctx = ssl.create_default_context()
    smtp_server: SMTP_Cfg = email_ntify.smtp
    error = None # The error message to print out at the end

    try:
        if smtp_server.ssl:
            # If SSL is enabled we need to use SMTP_SSL server
            server = smtplib.SMTP_SSL( smtp_server.server, smtp_server.port, context=ctx )
        else:
            server = smtplib.SMTP( smtp_server.server, smtp_server.port )
            server.ehlo()
            if not server.has_extn("starttls"):
                raise smtplib.SMTPException(
                    f"SMTP Server ({smtp_server.server, smtp_server.port}) has not TLS"
                )
            
            server.starttls(context=ctx)
            server.ehlo()
        
        with server:
            server.login(email_ntify.from_, email_ntify.password)
    
    except smtplib.SMTPAuthenticationError as e:
        error = "SMTP Authentication Error: Username and Password not accepted"
    except smtplib.SMTPException as e:
        error = f"SMTP Error: {e}"
    
    if args.verbose:
        result_str = "OK" if not error else "NO"
        print(f"    ({result_str}) Checking SMTP Server Authentication")

    return error

def check_notification_system( notification: NotificationCfg, args: Args ) -> Dict[str,str]:
    """ Checks the correctness of the notification system configuration
    in particular if all services are reachable. It returns a list of 
    successful notification system but, if none is reachable, then raise
    an AssertionError and exit. """
    if args.verbose:
        print("  [--] Notification system checks")

    errors = defaultdict(str)

    if notification.email is not None:
        errors["email"] = check_email_notification_system( 
            notification.email, args )
        
    if any( errors.values() ):
        error_msg = "\n[WARNING] Notification System Errors:\n  "
        error_msg += "\n".join( map( 
            lambda e: f"  - ({e[0]}) {e[1]}", 
            errors.items() ) )
        
        print(error_msg)
        
    return errors