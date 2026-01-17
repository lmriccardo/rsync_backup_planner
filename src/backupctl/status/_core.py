from backupctl.models.registry import Registry, Job
from backupctl.constants import *
from backupctl.utils.cron import *
from typing import Optional
from functools import partial

def check_consistency( registry: Registry, cronlist: CronList ) -> bool:
    """ This function checks consistency between the registry
    and the cronlist. Consistency checks that jobs in the registry
    mirror jobs registered into the cronlist. Each missed job
    is an error and should be solved using the `apply` command.
    Other consistency errors includes enabled jobs that are
    disabled in the other list, command mismatch and so on. """
    start_print = False

    # First check that if registry is empty also the cronlist shall be empty
    if ( (registry is None) ^ (cronlist is None) ):
        if not start_print:
            start_print = True
            print()

        print(" - (X) Registry and cronlist must both exsists or not")
        print()
        return False
    
    if registry is None and cronlist is None: return True
    
    # If both exists they must have the same number of jobs
    if len(registry) != len(cronlist):
        if not start_print:
            start_print = True
            print()

        print("- (X) Registry and cronlist must have the same number of jobs")
        print()
        return False

    # Even if the number of jobs matches, we need to check that they
    # have exactly the same jobs.
    registry_jobs = set(registry.keys())
    cronlist_jobs = set(cronlist.keys())
    jobs_diff = registry_jobs ^ cronlist_jobs

    if len(jobs_diff) > 0 and not start_print:
        start_print = True
        print()

    for job in jobs_diff:
        if job in registry_jobs:
            print(f"- (X) Job {job} in REGISTRY but not into CRONLIST ")
        else:
            if not start_print: print()
            print(f"- (X) Job {job} in CRONLIST but not into REGISTRY ")

    if len(jobs_diff) > 0: 
        print()
        return False

    # Once we have ensured that both registry and cronlist
    # have both the name number of jobs and the same jobs
    # we need to check for status and command
    return_status = True
    for job_name in registry_jobs:
        if not start_print:
            start_print = True
            print()
        
        print(f"[*] Consistency check for Job {job_name.upper()}")
        registry_job: Job = registry[job_name]
        cronlist_job      = cronlist[job_name]

        cronlist_enabled, cronlist_cmd = cronlist_job
        registry_enabled = registry_job.is_enabled()
        registry_cmd = registry_job.cmd

        # This check that both in the registry and cronlist the
        # job is either enabled or disabled
        if cronlist_enabled ^ registry_enabled:
            return_status = False
            print(
                "  (X) Enabled state mismatch:"
                f" REGISTRY={'ENABLED' if registry_enabled else 'DISABLED'},"
                f" CRONLIST={'ENABLED' if cronlist_enabled else 'DISABLED'}"
            )
        else:
            print(
                f"  (✓) Enabled state OK "
                f"({'ENABLED' if registry_enabled else 'DISABLED'})"
            )
        
        # Check for command mismatch
        if cronlist_cmd != registry_cmd:
            return_status = False
            print("  (X) Command mismatch:")
            print(f"     REGISTRY:  {registry_cmd}")
            print(f"     CRONLIST:  {cronlist_cmd}")
        else:
            print("  (✓) Command OK")

    print()
    return return_status

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

def make_registry_consistent( registry: Registry ) -> None:
    """ Makes the cronlist consistent with the entire registry """
    cronout = get_crontab_list() # Get the crontab list

    if registry is not None:
        # If there is at least something in the registry then
        # we can substitute those existing
        def cron_match_line( job: Job, cronline: str ) -> bool:
            return job.tag() in cronline
        
        for _, registry_job in registry.items():
            _cron_match_line = partial( cron_match_line, registry_job )
            wanted_cmd = registry_job.to_cron(with_tag=True)
            insert_cron_command(cronout, wanted_cmd, _cron_match_line)

    def not_registry_job( cronline: str ) -> bool:
        """ A cronline job is not into the registry """
        if CRONTAB_TAG_PREFIX not in cronline: return False
        _, name = cronline.split(CRONTAB_TAG_PREFIX)
        return registry is None or name not in registry

    # Then we also need to remove all jobs not belonging
    # to the registry from the cronlist
    insert_cron_command( cronout, None, not_registry_job )
    
    # Write it into cron
    write_to_cron( cronout )