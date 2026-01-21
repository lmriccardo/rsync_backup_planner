import subprocess

from typing import List, Callable, TypeAlias, Dict, Tuple
from backupctl.constants import CRONTAB_TAG_PREFIX, BACKUPCTL_RUN_COMMAND
from .exceptions import ExternalCommandError, ensure

CronMatchFn = Callable[[str],bool]
CronList: TypeAlias = Dict[str,Tuple[bool, str]] | None

def get_crontab_list() -> List[str]:
    """ Returns the list of all jobs actually registered on crontab """
    cronout = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    ok = cronout.returncode == 0 or ( cronout.returncode == 1 and len(cronout.stdout) == 0 )
    ensure(ok, f"(crontab -l) error: {cronout.stderr}", ExternalCommandError)
    return cronout.stdout.splitlines()

def write_to_cron( input_: str | List[str] ) -> None:
    """ Write the crontab from input """
    if isinstance(input_, list): input_ = "\n".join(input_)
    input_ = input_.rstrip("\n") + ("\n" if input_ != "" else "")
    out = subprocess.run(["crontab", "-"], input=input_, capture_output=True, text=True, check=False)
    ensure(out.returncode == 0, f"(crontab -) error: {out.stderr}", ExternalCommandError)

def insert_cron_command( cronlist: List[str], line: str | None, repl_match_fn: CronMatchFn ) -> None:
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

    # If the input is None then skip it
    if line is None: return

    # Insert the input line where it is supposed to be.
    if first_idx is None: first_idx = len(cronlist)
    cronlist.insert( first_idx, line )

def read_cronlist_jobs() -> CronList:
    """ Read the cronlist and returns all backupctl jobs
    that are listed there mapping the name to its command
    and enabled/disabled boolean state. """
    cronlist = get_crontab_list()
    cronlist_jobs = dict()

    # Early exit if there are no active/inactive jobs
    if not cronlist: return None

    for cronjob in cronlist:
        if CRONTAB_TAG_PREFIX not in cronjob:
            continue

        croncmd, name = cronjob.split(CRONTAB_TAG_PREFIX)
        enabled = not croncmd.startswith("#")
        if croncmd.find( BACKUPCTL_RUN_COMMAND ) == -1:
            raise RuntimeError(
                f"cronjob tagged {name} is not well formatted."
            )

        start_idx = 0 if enabled else 1
        cronlist_jobs[name] = (enabled, croncmd[start_idx:].strip())
    
    return cronlist_jobs
