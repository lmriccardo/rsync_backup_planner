import argparse

from backupctl.utils.exceptions import assertion_wrapper
from ._core import inspect_targets


@assertion_wrapper
def run(args: argparse.Namespace) -> None:
    blocks = inspect_targets(args.target)
    separator = "\n" + ("-" * 60) + "\n"
    print(separator.join(blocks))
