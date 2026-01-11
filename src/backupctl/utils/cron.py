import subprocess

from typing import List, Callable
from .exceptions import assert_1

CronMatchFn = Callable[[str],bool]

def get_crontab_list() -> List[str]:
    """ Returns the list of all jobs actually registered on crontab """
    cronout = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
    ok = cronout.returncode == 0 or ( cronout.returncode == 1 and len(cronout.stdout) == 0 )
    assert_1( ok, f"[ERROR] (crontab -l) error: {cronout.stderr}" )
    return cronout.stdout.splitlines()

def write_to_cron( input_: str | List[str] ) -> None:
    """ Write the crontab from input """
    if isinstance(input_, list): input_ = "\n".join(input_)
    input_ = input_.rstrip("\n") + "\n"
    out = subprocess.run(["crontab", "-"], input=input_, capture_output=True, text=True, check=False)
    assert_1( out.returncode == 0, f"[ERROR] (crontab -) error: {out.stderr}" )

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