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
from backupctl.utils.console import cerror, cinfo

def run( args: argparse.Namespace ) -> None:
    # Parse the input arguments
    args: Args = parse_input_arguments( args )

    # Load the configuration
    cinfo(f"[*] Loading configuration from {args.config_file}")
    conf = load_user_configuration( args.config_file )
    if conf.backup.targets and args.verbose:
        cinfo("[*] Available Targets are: ", end="")
        cinfo(", ".join(list(conf.backup.targets.keys())))
    
    if not conf.backup.targets:
        cerror("No available targets")
        return 0
    
    cinfo("[*] Creating backups plans")
    create_backups( conf, args )

    return 0
