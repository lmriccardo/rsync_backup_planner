import sys
import argparse
import json

from pathlib import Path
from backup_checks import *
from constants import *

@assertion_wrapper
def parse_input_arguments() -> Args:
    """ Parse and validates input arguments """
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Backup Plan configuration file")
    parser.add_argument("-v", "--verbose", help="Enable/Disable Verbosity", required=False, 
                        default=False, action="store_true")
    args = parser.parse_args()

    # Check that the input file is actually a file
    assert_1(Path(args.config).is_file(), f"Config '{args.config}' is not a file")
    assert_1(args.config.endswith('.yaml') or args.config.endswith('.yml'),
            f"Config '{args.config}' is not a YAML file")

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
            check_user_create_in_dir( exclude_out_folder_p )
            exclude_out_folder_p.mkdir( parents=True, exist_ok=True )

        # Create the path
        exclude_file_path = exclude_out_folder_p / f"{target_name}.exclude"
        check_user_create_in_dir( exclude_file_path )
        
        if not exclude_file_path.exists():
            exclude_file_path.touch()
        
        print(f"[*] Generating exclude file at {exclude_file_path}")
        content = "\n".join(rsync.excludes) + "\n"
        with open(exclude_file_path, mode='w', encoding='utf-8') as io:
            io.write( content )

        return exclude_file_path

    except PermissionError as _:
        assert_1(False, "Permission Error")

def generate_automation( 
    exclude_path: Path, 
    notitication_errors: Dict[str,str],
    target_name: str,
    target: Target, 
    args: Args 
) -> None:
    """ Generates the cronjob automation task """
    # First we need to create the JSON file for the plan configuration
    configuration_plan = dict()
    configuration_plan["name"] = target_name
    configuration_plan["log"] = (DEFAULT_LOG_FOLDER / target_name).__str__()
    configuration_plan["compression"] = target.rsync.compress

    # Create the command
    password_file = Path(target.remote.password_file).resolve().__str__()
    command = create_rsync_command(
        target.remote.host, target.remote.port, user=target.remote.user,
        password_file=password_file, module=target.remote.dest.module, 
        folder=target.remote.dest.folder, list_only=False, 
        progress=target.rsync.show_progress, includes=target.rsync.includes,
        verbose=target.rsync.verbose, exclude_from=exclude_path, 
        sources=target.rsync.sources, use_flags=True
    )
    
    configuration_plan["command"] = command

    # Now we need to put only those notification system that
    # successfully have passed the previous checks
    configuration_plan["notification"] = []
    curr_ns_identifier = 0
    for ns_name, ns_error in notitication_errors.items():
        if ns_error is not None: continue
        curr_ns_identifier += 1
        entry = { "id" : curr_ns_identifier }
        if ns_name == "email":
            # Create the email entry into the json
            entry["type"] = "email"
            entry["from"] = target.notification.email.from_
            entry["to"] = target.notification.email.to
            entry["password"] = target.notification.email.password
            entry["server"] = target.notification.email.smtp.server
            entry["port"] = target.notification.email.smtp.port
            entry["ssl"] = target.notification.email.smtp.ssl
        else:
            ...

        configuration_plan["notification"].append(entry)
    
    # Save the JSON configuration into the default folder
    DEFAULT_PLAN_CONF_FOLDER.mkdir(parents=True, exist_ok=True)
    plan_conf_path = DEFAULT_PLAN_CONF_FOLDER / f"{target_name}-plan.json"
    plan_conf_path.touch(exist_ok=True)

    if args.verbose:
        print("[*] Generated configuration plan:")
        print(json.dumps(configuration_plan, indent=2))
        print()

    print(f"[*] Saving configuration plan into {plan_conf_path}")
    with plan_conf_path.open(mode='w', encoding='utf-8') as io:
        json.dump( configuration_plan, io, indent=2 )

@assertion_wrapper
def consume_backup_target( name: str, target: Target, args: Args ) -> bool:
    print("\n" + "-" * 20 + f" TARGET: {name} " + "-" * 20)

    # First we need to validate the remaining part of the configuration
    # which does not depend on the YAML structure
    print("[*] Further configuration checks", end="\n" if not args.verbose else ":\n")
    check_remote_dest( target.remote, args )
    assert_1(check_exclude_file( target.rsync, args ),
        f"Exclude file {target.rsync.exclude_from}, does not exists")
    check_rsync_source_folders( target.rsync, args )
    notification_errors = check_notification_system( target.notification, args )

    # Preprocess excludes and include, finally creates the complete exclude file
    if args.verbose: print()
    print("[*] Preprocessing excludes and includes path")
    preprocess_excludes_includes( target.rsync )
    exclude_path = generate_exclude_file( target.rsync.exclude_output_folder, name, target.rsync )

    # Finally, generate the cronjob
    generate_automation( exclude_path, notification_errors, name, target, args )
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

def main():
    # Parse the input arguments
    args: Args = parse_input_arguments()

    # Load the configuration
    print(f"[*] Loading configuration from {args.config_file}")
    conf = load_configuration( args.config_file )
    if conf.backup.targets and args.verbose:
        print(f"[*] Available Targets are: ", end="")
        print(", ".join(list(conf.backup.targets.keys())))

    if not conf.backup.targets:
        print("No available targets")
        sys.exit(0)

    print("[*] Creating backups plans")
    create_backups( conf, args )

if __name__ == "__main__":
    main()