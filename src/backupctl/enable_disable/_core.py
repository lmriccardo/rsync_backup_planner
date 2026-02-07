from typing import List
from backupctl.constants import REGISTERED_JOBS_FILE
from backupctl.status._core import make_registry_consistent
from backupctl.models.registry import Registry, write_registry, JobStatusType
from backupctl.utils.console import cerror, csuccess

def modify_targets_state( 
    targets: List, registry: Registry, status: JobStatusType
) -> None:
    """ Modify the status of all input targets of the registry """
    for target in targets:
        if target not in targets:
            cerror(f"- (X) Target {target} not a job in the registry")
            continue
            
        # Change the status of the target
        registry[target].status = status
        csuccess(f"- (✓) Target {target.upper()} status modified to {status}")

    # Write the registry back to the file
    write_registry( REGISTERED_JOBS_FILE, registry )

    # Makes the cronlist consistent with the registry
    make_registry_consistent( registry )
