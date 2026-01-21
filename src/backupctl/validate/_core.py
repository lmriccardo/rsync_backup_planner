import backupctl.models.user_config as user_cfg
import socket
import os

from backupctl.models.rsync import RSyncStatus
from backupctl.utils.rsync import run_rsync_command
from backupctl.models.user_config import *
from backupctl.models.filesystem import *
from backupctl.utils.exceptions import (
    BackupCtlError,
    InputValidationError,
    PermissionDeniedError,
    ensure,
)

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Args:
    config_file: Path # The configuration file for the plan
    verbose: bool # Enable/Disable Verbosity

def user_can_create_in_dir( path: Path ) -> None:
    """ Checks if the current user can access the parent path of either
    the input folder or file the user would like to create/excute/read
    """
    path = path.resolve()
    
    # Here we should also check that the parent folder exists
    # otherwise we need to recurse with the parent input
    if not path.parent.exists():
        return user_can_create_in_dir( path.parent )

    if not os.access(path.parent, os.W_OK | os.X_OK):
        print_permission_error(path, with_parent=True)
        raise PermissionDeniedError("Permission error")

def user_can_read_in_dir( path: Path ) -> None:
    """ Check if the current user has read permissions on the folder/file """
    path = path.resolve()
    # Here we should also check that the parent folder exists
    # otherwise we need to recurse with the parent input
    if not path.parent.exists():
        return user_can_read_in_dir( path.parent )

    if not os.access(path.parent, os.R_OK):
        print_permission_error(path)
        raise PermissionDeniedError("Permission error")

def check_sock_connection( remote: Remote, args: Args ) -> bool:
    """ Checks the remote connection to the rsync server """
    remote_ip = "<unresolved>"
    try:
        remote_ip = socket.gethostbyname(remote.host)
    except OSError:
        if args.verbose:
            print(
                f"  (NO) Checking connection to {remote.host} ({remote_ip}) on {remote.port}"
            )
        return False

    if args.verbose:
        print(
            f"  ( ) Checking connection to {remote.host} ({remote_ip}) on {remote.port}",
            end="",
        )

    result = False
    try:
        with socket.create_connection((remote_ip, remote.port), timeout=2.0):
            result = True
    except OSError:
        ...

    if args.verbose:
        result_str = "OK" if result else "NO"
        print(
            f"\r  ({result_str}) Checking connection to {remote.host} ({remote_ip}) on {remote.port}"
        )

    return result

def _check_rsync_module_auth( remote: Remote ) -> RSyncStatus:
    """ Checks authentication to the remote rsync host and if the module exists """
    # First check that the password_file exists
    if remote.password_file is not None:
        ensure(
            Path(remote.password_file).absolute().is_file(),
            f"Password file {remote.password_file} does not exists",
            InputValidationError,
        )

    password_file = None if not remote.password_file else \
        Path(remote.password_file).absolute().__str__()    
    
    output = run_rsync_command(
        host=remote.host, 
        port=remote.port,
        user=remote.user,
        password_file=password_file,
        list_only=True,
        prune_empty_dirs=False,
        numeric_ids=False,
        module=remote.dest.module,
        folder=remote.dest.folder
    )

    return output.status

def check_remote_module_auth( remote: Remote, args: Args ) -> None:
    """ Checks remote authentication with the remote rsync host """
    status = _check_rsync_module_auth( remote )

    if args.verbose:
        print("  [--] Remote module and folder authentication")
        
    # Module exists
    inner_result = status != RSyncStatus.UNKNOWN_MODULE
    result_str = "OK" if inner_result else "NO"

    if args.verbose: print(f"    ({result_str}) Checking for remote module: {remote.dest.module}")
    ensure(inner_result, "Destination Module not found", InputValidationError)

    # Authentication check
    inner_result = status != RSyncStatus.AUTH_FAILED
    result_str = "OK" if inner_result else "NO"
    password_file = "<empty>"
    if remote.password_file:
        password_file=Path(remote.password_file).absolute().__str__()
    
    if args.verbose:
        print((
            f"    ({result_str}) Checking auth with username " +
            ("<empty>" if not remote.user else remote.user) +
            f" and password file {password_file}"
        ))

    ensure(inner_result, "Authentication failed", InputValidationError)

    # Folder check
    inner_result = status != RSyncStatus.FOLDER_NOT_FOUND
    result_str = "OK" if inner_result else "NO"

    if args.verbose:
        print(f"    ({result_str}) Checking for remote folder: {remote.dest.module}/{remote.dest.folder}")
    
    ensure(inner_result, "Destination Folder not found", InputValidationError)

def check_remote_dest(remote: Remote, args: Args) -> bool:
    """ Checks if the remote destination exists """
    ensure(check_sock_connection(remote, args), "Connection to remote failed", InputValidationError)
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

        ensure(
            result,
            f"Source folder {source_folder_path} does not exists or cannot be read!",
            InputValidationError,
        )
        
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

def check_notification_system( notification: NotificationCfg, args: Args ) -> None:
    """ Checks the correctness of the notification system configuration
    in particular if all services are reachable. It returns a list of 
    successful notification system but, if none is reachable, then raise
    a validation error and exit. """
    if args.verbose:
        print("  [--] Notification system checks")

    errors = defaultdict(str)

    # Check email notification system if provided
    if notification.email is not None:
        error = check_email_notification_system( notification.email, args )
        if error is not None: notification.email = None
        errors["email"] = error

    # Check for webhooks notification system if provided
    # ...
        
    if any( errors.values() ) and args.verbose:
        error_msg = "\n[WARNING] Notification System Errors:\n  "
        error_msg += "\n".join( map( 
            lambda e: f"  - ({e[0]}) {e[1]}", 
            errors.items() ) )
        
        print(error_msg)

def validate_target( target: user_cfg.NamedTarget, args: Args ) -> None:
    """ Validates a single target against some checks """
    # Checking if remote destination is reachable
    check_remote_dest( target.remote, args )
    ensure(
        check_exclude_file(target.rsync, args),
        f"Exclude file {target.rsync.exclude_from}, does not exists",
        InputValidationError,
    )
    
    check_rsync_source_folders( target.rsync, args )
    check_notification_system( target.notification, args )

def validate_configuration( config: user_cfg.YAML_Conf ) -> int:
    """ Validates all targets in the user provided configuration """
    # If there are no targets, skip
    if not config.backup.targets:
        print("No Targets to be validated")
        return
    
    args = Args(None, False) # Some additional arguments
    exit_code = 0

    for target_name, target in config.backup.targets.items():
        try:
            print(f"- (  ) Validating Target {target_name}", end="", flush=True)
            target_with_name = user_cfg.NamedTarget.from_target(target_name, target)
            validate_target( target_with_name, args )
            print(f"\r- (OK) Validation completed for Target {target_name}")
        except BackupCtlError as e:
            print(f"\r- (NO) Validation completed for Target {target_name}")
            print(f"[ERROR] {e}")
            exit_code = 1
    
    return exit_code
