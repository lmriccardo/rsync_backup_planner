import argparse
import backupctl.register.cmd as register
import backupctl.status.cmd as status
import backupctl.validate.cmd as validate

def main():
    parser = argparse.ArgumentParser(prog="backupctl")
    sub = parser.add_subparsers(required=True)
    
    # Create the: backupctl register COMMAND
    p_plan = sub.add_parser("register", help="Create and register a new backup plan")
    p_plan.set_defaults(func=register.run)
    p_plan.add_argument("config", help="Backup Plan configuration file")
    p_plan.add_argument(
        "-v", "--verbose", 
        help="Enable/Disable Verbosity", 
        required=False, 
        default=False, 
        action="store_true"
    )

    # Create the: backupctl validate COMMAND
    p_validate = sub.add_parser("validate", help="Validate a user configuration")
    p_validate.set_defaults(func=validate.run)
    p_validate.add_argument("config", help="The configuration file to validate", type=str)

    # Create the: backupctl status COMMAND
    p_check = sub.add_parser("status", help="High-level health check")
    p_check.set_defaults(func=status.run)
    p_check.add_argument(
        "--apply", 
        help="Automatically solve errors", 
        action="store_true", 
        default=False
    )

    # Create the: backupctl remove COMMAND

    # Create the: backupctl enable COMMAND

    # Create the: backupctl disable COMMAND

    # Create the: backupctl list

    # Create the: backupctl run COMMAND

    args = parser.parse_args()
    args.func(args)
    return 0