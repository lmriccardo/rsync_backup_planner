import argparse

from backupctl.models.registry import read_registry, JobStatusType
from ._core import modify_targets_state
from backupctl.utils.console import cerror, cwarn

def run_enable( args: argparse.Namespace ) -> None:
    return run( args, True )

def run_disable( args: argparse.Namespace ) -> None:
    return run( args, False )

def run( args: argparse.Namespace, enable: bool=True ) -> None:
    try:
        # Load the registry first to get all targets
        registry = read_registry()
        if not registry:
            cwarn("[*] Registry is empty, so nothing to be removed.")
            return 0

        # Get all jobs to be removed and remove them from the registry
        # and also the cronlist to keeps things consistent
        target_jobs = args.target or registry.keys()
        new_status = JobStatusType.enabled if enable else JobStatusType.disabled
        modify_targets_state( target_jobs, registry, new_status)

        return 0

    except Exception as e:
        cerror(f"[ERROR] {e}")
        return 1
