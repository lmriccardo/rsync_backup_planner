import argparse

from backupctl.models.registry import read_registry
from ._core import remove_targets
from backupctl.utils.console import cerror, cwarn

def run( args: argparse.Namespace ) -> None:
    try:
        # Load the registry first to get all targets
        registry = read_registry()
        if not registry:
            cwarn("[*] Registry is empty, so nothing to be removed.")
            return 0

        # Get all jobs to be removed and remove them from the registry
        # and also the cronlist to keeps things consistent
        target_jobs = args.target or registry.keys()
        remove_targets( target_jobs, registry )

        return 0

    except Exception as e:
        cerror(f"[ERROR] {e}")
        return 1
