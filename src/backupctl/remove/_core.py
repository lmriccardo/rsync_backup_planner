import shutil

from typing import List
from backupctl.constants import *
from backupctl.status._core import make_registry_consistent
from backupctl.models.registry import Registry, write_registry

def remove_targets( targets: List, registry: Registry ) -> None:
    """ Remove a job from the registry if it exists """
    removed_targets = []
    for target in targets:
        if target not in registry:
            print(f"- (X) Target {target} not a job in the registry")
            continue
        
        # Remove the target from the registry dict
        print(f"- [ ] Target: {target.upper()}")
        removed_targets.append(target)

        print("      + Wiping out the registry entry")
        registry.pop( target )

        # Delete all files releated to that target: JSON 
        # configuration, the log folder and the .exclude file
        exclude_file = DEFAULT_EXCLUDE_FOLDER / f"{target}.exclude"
        log_folder   = DEFAULT_LOG_FOLDER / target
        config_file  = DEFAULT_PLAN_CONF_FOLDER / f"{target}{DEFAULT_PLAN_SUFFIX}"

        print(f"      + Removing exclude file {exclude_file}")
        exclude_file.unlink( missing_ok=True )
        
        print(f"      + Removing log folder {log_folder}")
        shutil.rmtree( log_folder )
        
        print(f"      + Removing configuration file {config_file}")
        config_file.unlink( missing_ok=True )

        print()
        
    # Write the registry back to the file
    write_registry( REGISTERED_JOBS_FILE, registry )

    # Makes the cronlist consistent with the registry
    make_registry_consistent( registry )

    log_message = " - (✓) Target {} removed successfully"
    format_log = lambda x: log_message.format(x.upper())
    print("\n".join(map( format_log, removed_targets )))