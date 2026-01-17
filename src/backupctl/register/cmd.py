"""
@author: Riccardo La Marca
@title: Check Command

This command takes a user configuration and installs all
available and validated targets into the system, i.e., 
REGISTRY file and cronlist (if LINUX). It reads the input
configuration and generates a new JSON configuration into
the `~/.backups/plan/` folder named after the target.
"""

import argparse

from ._core import parse_input_arguments, \
    Args, \
    load_user_configuration, \
    create_backups

def run( args: argparse.Namespace ) -> None:
    # Parse the input arguments
    args: Args = parse_input_arguments( args )

    # Load the configuration
    print(f"[*] Loading configuration from {args.config_file}")
    conf = load_user_configuration( args.config_file )
    if conf.backup.targets and args.verbose:
        print(f"[*] Available Targets are: ", end="")
        print(", ".join(list(conf.backup.targets.keys())))
    
    if not conf.backup.targets:
        print("No available targets")
        return 0
    
    print("[*] Creating backups plans")
    create_backups( conf, args )

    return 0