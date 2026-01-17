"""
@author: Riccardo La Marca
@title: Check Command

This command performs an high-level healthcheck of the
entire system, meaning available registry, cron entries,
consistency between the registry and the cronlist, last
status run of all registered targets and so on. For this
kind of check the REGISTRY file is the source of truth.
"""

import argparse

from backupctl.models.registry import read_registry
from ._core import *

def run( args: argparse.Namespace ) -> None:
    try:
        print("[*] Starting helthcheck")

        # Load the registry with all jobs
        registry = read_registry()
        registry_size = 0 if registry is None else len(registry)
        print(f"[*] Registry loaded from {REGISTERED_JOBS_FILE} ({registry_size})")

        # Load the cronlist
        cronlist = read_cronlist_jobs()
        cronlist_len = 0 if cronlist is None else len(cronlist)
        print(f"[*] Cronlist loaded ({cronlist_len})")

        if ( check_consistency(registry, cronlist) ):
            print("[*] Consistency Check terminated SUCCESSFULLY.")
            return
        
        print("\n[*] Consistency Check FAILED.\n")
        print(
            "NOTE: By solving inconsistencies the entire registry will\n"
            "      be written into the cronlist. Non-releated cronjob\n"
            "      will be preserved, while all backupctl cronjobs  not\n"
            "      belonging to the registry will be wiped out.\n"
        )

        if not args.apply_fix:
            user_in = input("Would You like to solve errors? [Y/N, BLANK=YES] ")
            if user_in != "" and user_in.upper() == "N": return

        make_registry_consistent( registry )
        return 0

    except KeyboardInterrupt:
        print("\n[*] CTRL+C - Exiting")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1