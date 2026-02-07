"""
@author: Riccardo La Marca
@title: Check Command

This command is used to perform a quick validation
of the input user-configuration according to the
YAML schema format provided by the pydantic models
in the `modules` python sub-module.
"""

import argparse
import backupctl.models.user_config as user_cfg

from ._core import validate_configuration
from backupctl.utils.console import cerror, cinfo
from backupctl.utils.exceptions import InputValidationError, ensure
from pathlib import Path
from pydantic import ValidationError

def run( args: argparse.Namespace ) -> None:
    conf_file = Path(args.config).expanduser().resolve()
    ensure(conf_file.is_file(), f"Config '{args.config}' is not a file", InputValidationError)
    result = 0

    try:
        # Load the configuration file. A first validation step is
        # done at this point, since pydantic will load the
        # configuration into the YAML_Conf class only if its
        # validation step is successful
        cinfo(f"[*] Loading configuration: {conf_file}\n")
        configuration = user_cfg.load_user_configuration(conf_file)
        result = validate_configuration( configuration )
    
    except ValidationError as e:
        cerror(f"\n[ERROR] Invalid configuration format detected:\n{e}")
        result = 1
    
    finally:
        cinfo(f"\n[*] Validation completed with exit code: {result}")
        return result
