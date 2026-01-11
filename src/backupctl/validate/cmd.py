import argparse
import backupctl.models.user_config as user_cfg

from .checks import *
from backupctl.utils.exceptions import assert_1
from pathlib import Path
from pydantic import ValidationError

def validate_target( target: user_cfg.NamedTarget, args: Args ) -> None:
    """ Validates a single target against some checks """
    # Checking if remote destination is reachable
    check_remote_dest( target.remote, args )
    assert_1(check_exclude_file( target.rsync, args ),
        f"Exclude file {target.rsync.exclude_from}, does not exists")
    
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
        except AssertionError as e:
            print(f"\r- (NO) Validation completed for Target {target_name}")
            print(f"[ERROR] {e}")
            exit_code = 1
    
    return exit_code

def run( args: argparse.Namespace ) -> None:
    conf_file = Path(args.config).expanduser().resolve()
    assert_1(conf_file.is_file(), f"Config '{args.config}' is not a file")

    try:
        # Load the configuration file. A first validation step is
        # done at this point, since pydantic will load the
        # configuration into the YAML_Conf class only if its
        # validation step is successful
        print(f"[*] Loading configuration: {conf_file}\n")
        configuration = user_cfg.load_user_configuration(conf_file)
        result = validate_configuration( configuration )
    
    except ValidationError as e:
        print(f"\n[ERROR] Invalid configuration format detected:\n{e}")
        result = 1
    
    finally:
        print(f"\n[*] Validation completed with exit code: {result}")
        return result