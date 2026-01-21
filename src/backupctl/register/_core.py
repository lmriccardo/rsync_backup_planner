import argparse
import sys
import json
import shlex

from backupctl.status._core import make_job_consistent
from backupctl.validate._core import validate_target
from backupctl.validate._core import Args, user_can_create_in_dir
from backupctl.utils.exceptions import (
    InputValidationError,
    PermissionDeniedError,
    assertion_wrapper,
    ensure,
)

from backupctl.models.plan_config import \
    load_from_target, write_plan_configuration

from backupctl.models.user_config import *
from backupctl.models.registry import *
from backupctl.constants import *
from backupctl.utils.cron import *

@assertion_wrapper
def parse_input_arguments( args: argparse.Namespace ) -> Args:
    """ Parse and validates input arguments """
    # Check that the input file is actually a file
    ensure(
        Path(args.config).is_file(),
        f"Config '{args.config}' is not a file",
        InputValidationError,
    )
    ensure(
        args.config.endswith(".yaml") or args.config.endswith(".yml"),
        f"Config '{args.config}' is not a YAML file",
        InputValidationError,
    )

    return Args( Path(args.config).absolute(), args.verbose )

def preprocess_excludes_includes( rsync: RsyncCfg ) -> None:
    """ Preprocess all excludes and includes by flattening all the excludes
    both from the list and from the exclude_from file and removes those
    under the includes keyword. """
    # First we need to read all the excludes from the exclude file
    excludes = rsync.excludes
    if rsync.exclude_from:
        iostream = open(rsync.exclude_from, mode='r', encoding='utf-8')
        while ( line := iostream.readline() ):
            line = line.strip()
            if not line: continue
            if line.startswith("#"): continue
            excludes.append(line)
        iostream.close()
    
    # Set all excludes into the exclude list and reset
    # the exclude_from field from the configuration 
    rsync.excludes = excludes
    rsync.exclude_from =  None

    if not rsync.includes: return

    # Otherwise, if some includes path matches exclude ones remove those path from 
    # the excludes. Otherwise, in case the match is partial (meaning that matches 
    # against a generic wildcard pattern) then do nothing.
    for include_path in rsync.includes:
        if include_path in rsync.excludes:
            rsync.excludes.remove(include_path)

def generate_exclude_file( exclude_out_folder: str | None, target_name: str, rsync: RsyncCfg ) -> Path:
    """ Creates the new exclude file from the given rsync config """
    # Create the parent path if not exists
    if not exclude_out_folder:
        exclude_out_folder = DEFAULT_EXCLUDE_FOLDER

    try:
        # Check is the user can create the exclude folder or the exclude file
        exclude_out_folder_p = Path( exclude_out_folder )

        if not exclude_out_folder_p.exists():
            user_can_create_in_dir( exclude_out_folder_p )
            exclude_out_folder_p.mkdir( parents=True, exist_ok=True )

        # Create the path
        exclude_file_path = exclude_out_folder_p / f"{target_name}.exclude"
        user_can_create_in_dir( exclude_file_path )
        
        if not exclude_file_path.exists():
            exclude_file_path.touch()
        
        print(f"[*] Generating exclude file at {exclude_file_path}")
        content = "\n".join(rsync.excludes) + "\n"
        with open(exclude_file_path, mode='w', encoding='utf-8') as io:
            io.write( content )

        return exclude_file_path

    except PermissionError as _:
        raise PermissionDeniedError("Permission Error")

def create_cronjob( name: str, backup_conf_path: Path, schedule: Schedule, args: Args ) -> None:
    """ Registers a new cronjobs if it does not exists yet """
    # Format the correct cron command
    cron_command = f"{schedule.to_cron()} {BACKUPCTL_RUN_COMMAND} run --log --notify {name}"

    registered = load_registry( REGISTERED_JOBS_FILE ) # Get all registered jobs
    curr_crontab_list = get_crontab_list() # Read the current crontab. Empty is OK

    current_job = Job( name, cron_command, JobStatusType.enabled )

    if name in registered:
        current_job = registered[name]
        if args.verbose:
            print(f"[*] Automation Task {name} already registered")
            print(f"    Registry Command: {cron_command}")
            print(f"    Registry Status : {current_job.status.value}")
            print(f"\n[*] Checking consistency with the crontab list")
    else:
        if args.verbose:
            print(f"[*] Registering for {name}")
            print(f"    Command: {cron_command}")

    make_job_consistent(current_job, curr_crontab_list)
    registered[name] = current_job
    write_registry( REGISTERED_JOBS_FILE, registered )

def create_automation_task( name: str, backup_conf_path: Path, schedule: Schedule, args: Args ) -> None:
    """ Creates the automation task. In Linux it will install a new cronjob. """
    print("[*] Installing the automation task")
    if sys.platform == "linux":
        create_cronjob( name, backup_conf_path, schedule, args )

def generate_automation( target: NamedTarget, args: Args ) -> None:
    """ Generates the cronjob automation task """
    # First we need to create the JSON file for the plan configuration
    configuration_plan = load_from_target(target)
    
    # Save the JSON configuration into the default folder
    DEFAULT_PLAN_CONF_FOLDER.mkdir(parents=True, exist_ok=True)
    plan_conf_path = DEFAULT_PLAN_CONF_FOLDER / f"{target.name}{DEFAULT_PLAN_SUFFIX}"

    if args.verbose:
        print("[*] Generated configuration plan:")
        print(json.dumps(configuration_plan.asdict(), indent=2))
        print()

    print(f"[*] Saving configuration plan into {plan_conf_path}")
    write_plan_configuration(plan_conf_path, configuration_plan)

    # Finally, creates the automation task
    create_automation_task( target.name, plan_conf_path, target.schedule, args )

@assertion_wrapper
def consume_backup_target( name: str, target: Target, args: Args ) -> bool:
    print("\n" + "-" * 20 + f" TARGET: {name} " + "-" * 20)
    target = NamedTarget.from_target(name, target)

    # First we need to validate the remaining part of the configuration
    # which does not depend on the YAML structure
    print("[*] Further configuration checks", end="\n" if not args.verbose else ":\n")
    validate_target( target, args )

    # Preprocess excludes and include, finally creates the complete exclude file
    if args.verbose: print()
    print("[*] Preprocessing excludes and includes path")
    preprocess_excludes_includes( target.rsync )

    exclude_path = generate_exclude_file( target.rsync.exclude_output_folder, name, target.rsync )
    target.rsync.exclude_from = str(exclude_path.expanduser().resolve())

    # Create the log folder if it does not exists
    log_folder = DEFAULT_LOG_FOLDER / target.name
    log_folder.mkdir(exist_ok=True, parents=True)

    # Finally, generate the cronjob
    generate_automation( target, args )
    return True

def create_backups( conf: YAML_Conf, args: Args ) -> None:
    """ Create backup files and cronjob for each target based on configuration """
    exclude_out_folder = conf.backup.exclude_output
    successful = []
    for target_name, target in conf.backup.targets.items():
        if not target.rsync.exclude_output_folder:
            target.rsync.exclude_output_folder = exclude_out_folder

        result = consume_backup_target( target_name, target, args )
        if not result:
            print("[*] FAILED ... Skipping to the next one")
            continue
        
        successful.append(target_name)
    
    print("\n[*] FINISHED! Successful targets: " + ", ".join(successful))
