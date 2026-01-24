import argparse
import sys
import backupctl.register.cmd as register
import backupctl.status.cmd as status
import backupctl.validate.cmd as validate
import backupctl.remove.cmd as remove
import backupctl.enable_disable.cmd as enable_disable
import backupctl.run.cmd as run
import backupctl.list.cmd as list_
import backupctl.inspect.cmd as inspect_
from backupctl.utils.version import format_version_output

def add_bool_argument(
    parser: argparse.ArgumentParser, *arg_name: str, help: str="", 
    action: str="store_true", default: bool=False
) -> None:
    parser.add_argument(*arg_name, action=action, 
        help=help, default=default)

def main():
    if "--version" in sys.argv:
        print(format_version_output())
        return 0

    parser = argparse.ArgumentParser(
        prog="backupctl",
        description="Backup control and consistency tool",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information",
    )
    sub = parser.add_subparsers(required=True)
    
    # Create the: backupctl register COMMAND
    p_plan = sub.add_parser("register", help="Create and register a new backup plan")
    p_plan.set_defaults(func=register.run)
    p_plan.add_argument("config", help="Backup Plan configuration file")
    add_bool_argument(p_plan, "-v", "--verbose", help="Enable/Disable Verbosity")

    # Create the: backupctl validate COMMAND
    p_validate = sub.add_parser("validate", help="Validate a user configuration")
    p_validate.set_defaults(func=validate.run)
    p_validate.add_argument("config", help="The configuration file to validate", type=str)

    # Create the: backupctl status COMMAND
    p_check = sub.add_parser("status", help="High-level health check")
    p_check.set_defaults(func=status.run)
    add_bool_argument(p_check, "--apply-fix", help="Automatically solve errors")

    # Create the: backupctl remove COMMAND
    p_remove = sub.add_parser("remove", help="Remove all or a list of specified jobs")
    p_remove.set_defaults(func=remove.run)
    p_remove.add_argument("--target", nargs="+", help="List of target jobs to remove")

    # Create the: backupctl enable COMMAND
    p_enable = sub.add_parser("enable", help="Enable all or a list of specified jobs")
    p_enable.set_defaults(func=enable_disable.run_enable)
    p_enable.add_argument("--target", nargs="+", help="List of target jobs to enable")

    # Create the: backupctl disable COMMAND
    p_disable = sub.add_parser("disable", help="Disable all or a list of specified jobs")
    p_disable.set_defaults(func=enable_disable.run_disable)
    p_disable.add_argument("--target", nargs="+", help="List of target jobs to disable")

    # Create the: backupctl run COMMAND
    p_run = sub.add_parser("run", help="Run a specified job")
    p_run.set_defaults(func=run.run)
    p_run.add_argument("target", help="The job to run", type=str)
    add_bool_argument(p_run, "--notify", help="Enable notifications")
    add_bool_argument(p_run, "--log", help="Enable file logging")
    add_bool_argument(p_run,"--dry-run", help="Run rsync command in dry-run mode")

    # Create the: backupctl list
    p_list = sub.add_parser("list", help="List jobs in the registry or cronlist")
    p_list.set_defaults(func=list_.run)
    g = p_list.add_mutually_exclusive_group()
    add_bool_argument(p_list, "--registry", help="list jobs from registry") 
    add_bool_argument(p_list, "--cron", help="list jobs from crontab")
    add_bool_argument(g, "--enabled", help="Selects only enabled tasks")
    add_bool_argument(g, "--disabled", help="Selects only disabled tasks")

    # Create the: backupctl inspect
    p_inspect = sub.add_parser("inspect", help="Inspect a registered target")
    p_inspect.set_defaults(func=inspect_.run)
    p_inspect.add_argument(
        "--target",
        nargs="+",
        help="List of target jobs to inspect (default: all)",
    )

    print(format_version_output())
    args = parser.parse_args()
    args.func(args)
    return 0
