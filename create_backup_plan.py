import sys
import argparse
import json
import shlex

from pathlib import Path
from typing import Tuple
from backup_checks import *
from constants import *

CronMatchFn = Callable[[str],bool]

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

def get_all_user_plans() -> List[str]:
    """ Retrieves as list of all user plans """
    user_plans = []
    for subpath in DEFAULT_PLAN_CONF_FOLDER.iterdir():
        *_, json_conf_file = subpath.parts
        if not json_conf_file.endswith(".json"): continue
        user_plans.append( json_conf_file.removesuffix(DEFAULT_PLAN_SUFFIX) )
    return user_plans

def get_all_registered_jobs() -> Dict[str,Job]:
    """ Returns all registered jobs """
    if not REGISTERED_JOBS_FILE.exists(): 
        REGISTERED_JOBS_FILE.touch()
        return dict()

    with REGISTERED_JOBS_FILE.open('r', encoding='utf-8') as io:
        registered_jobs = defaultdict(Job)
        while (line := io.readline()):
            name, *cmd, status = line.strip().removesuffix("\n").split()
            registered_jobs[name] = Job(name, " ".join(cmd), 
                JobStatusType.fromstr(status))
        
        return registered_jobs

def get_crontab_list() -> List[str]:
    """ Returns the list of all jobs actually registered on crontab """
    cronout = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    ok = cronout.returncode == 0 or ( cronout.returncode == 1 and len(cronout.stdout) == 0 )
    assert_1( ok, f"[ERROR] (crontab -l) error: {cronout.stderr}" )
    return cronout.stdout.splitlines()

def insert_cron_command( cronlist: List[str], line: str, repl_match_fn: CronMatchFn ) -> None:
    """ Removes from the cronlist the line matching the input one.
    repl_match is a function that takes as input the current cron line 
    and returns whether or not that line shalle be replaced. If the
    match is found than the line is replaced otherwise it is appended. """
    # Removes all matches to handle unwanted duplicates
    first_idx = None
    current_idx = 0

    while current_idx < len(cronlist):
        if repl_match_fn(cronlist[current_idx]):
            if first_idx is None: first_idx = current_idx
            cronlist.pop(current_idx)
            continue

        current_idx += 1

    # Insert the input line where it is supposed to be.
    if first_idx is None: first_idx = len(cronlist)
    cronlist.insert( first_idx, line )

def write_to_cron( input_: str | List[str] ) -> None:
    """ Write the crontab from input """
    if isinstance(input_, list): input_ = "\n".join(input_)
    input_ = input_.rstrip("\n") + "\n"
    out = subprocess.run(["crontab", "-"], input=input_, capture_output=True, text=True, check=False)
    assert_1( out.returncode == 0, f"[ERROR] (crontab -) error: {out.stderr}" )

def make_job_consistent( job: Job, cronout: Optional[List[str]] = None ) -> None:
    """ Makes the crontab entry releated to a job consistent with the registry """
    wanted_cmd = job.to_cron(with_tag=True)

    # Get the cron output if not passed as input
    if cronout is None: cronout = get_crontab_list()

    def cron_match_line( cronline: str ) -> bool:
        return job.tag() in cronline

    # Check for the line with the backupctl tag
    insert_cron_command( cronout, wanted_cmd, cron_match_line )

    # Write it into cron
    write_to_cron(cronout)

def write_to_registry( registry: Dict[str, Job] ) -> None:
    """ Overwrite the entire registry with the one in input """
    # Create the registry file if it does not exists
    try:
        if not REGISTERED_JOBS_FILE.exists(): REGISTERED_JOBS_FILE.touch()
        content = "\n".join( map(str, registry.values()) )
        REGISTERED_JOBS_FILE.write_text( content, encoding='utf-8' )
    except Exception as e:
        assert_1(False, f"[ERROR] Registry writing: {e}")

def create_cronjob( name: str, backup_conf_path: Path, schedule: Schedule, args: Args ) -> None:
    """ Registers a new cronjobs if it does not exists yet """
    # Format the correct cron command
    plan_arg = shlex.quote(str(backup_conf_path))
    cron_command = f"{schedule.to_cron()} {BACKUPCTL_RUN_COMMAND} run {plan_arg}"

    registered = get_all_registered_jobs() # Get all registered jobs
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
    write_to_registry( registered )

def create_automation_task( name: str, backup_conf_path: Path, schedule: Schedule, args: Args ) -> None:
    """ Creates the automation task. In Linux it will install a new cronjob. """
    print("[*] Installing the automation task")
    if sys.platform == "linux":
        create_cronjob( name, backup_conf_path, schedule, args )

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
    configuration_plan["compression"] = target.rsync.options.compress

    # Create the command
    password_file = Path(target.remote.password_file).resolve().__str__()
    command = create_rsync_command(
        target.remote.host, target.remote.port, user=target.remote.user,
        password_file=password_file, module=target.remote.dest.module, 
        folder=target.remote.dest.folder, list_only=False, 
        progress=target.rsync.options.show_progress, includes=target.rsync.includes,
        verbose=target.rsync.options.verbose, exclude_from=exclude_path, 
        sources=target.rsync.sources, use_flags=True,
        delete=target.rsync.options.delete, 
        itemize_changes=target.rsync.options.itemize_changes
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
    plan_conf_path = DEFAULT_PLAN_CONF_FOLDER / f"{target_name}{DEFAULT_PLAN_SUFFIX}"
    plan_conf_path.touch(exist_ok=True)

    if args.verbose:
        print("[*] Generated configuration plan:")
        print(json.dumps(configuration_plan, indent=2))
        print()

    print(f"[*] Saving configuration plan into {plan_conf_path}")
    with plan_conf_path.open(mode='w', encoding='utf-8') as io:
        json.dump( configuration_plan, io, indent=2 )

    # Finally, creates the automation task
    create_automation_task( target_name, plan_conf_path, target.schedule, args )

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