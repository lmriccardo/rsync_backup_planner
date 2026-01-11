import argparse
import backupctl.register.cmd as register
import backupctl.check.cmd as check
import backupctl.validate.cmd as validate

def main():
    parser = argparse.ArgumentParser(prog="backupctl")
    sub = parser.add_subparsers(required=True)
    
    # Create the: backupctl plan COMMAND
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

    # Create the: backupctl check COMMAND
    p_check = sub.add_parser("check", help="Check system state for problems")
    p_check.set_defaults(func=check.run)

    args = parser.parse_args()
    args.func(args)
    return 0