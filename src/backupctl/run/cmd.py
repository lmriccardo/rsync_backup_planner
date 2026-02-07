import argparse

from ._core import run_job
from backupctl.models.registry import read_registry
from backupctl.utils.console import cerror, cwarn

def run( args: argparse.Namespace ) -> None:
    try:
        # Get all the arguments to the command
        target = args.target
        notifications_en = args.notify
        logging_en = args.log
        dry_run_en = args.dry_run
        

        # Performs a first check that the target is in the registry
        registry = read_registry()
        if registry is None or target not in registry:
            cwarn(f"[*] Target {target} is not a job in the registry")
            return 0
        
        # Otherwise, run the job
        run_job( target, dry_run_en, notifications_en, logging_en )
        return 0
        
    except Exception as e:
        cerror(f"[ERROR] {e}")
        return 1
