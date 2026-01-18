import argparse

from ._core import list_tasks

def run( args: argparse.Namespace ) -> None:
    try:
        registry_en = args.registry
        cronlist_en = args.cron
        enabled_en  = args.enabled
        disabled_en = args.disabled

        registry_en_ = registry_en or not bool(( registry_en ^ cronlist_en ))
        cronlist_en_ = cronlist_en or not bool(( registry_en ^ cronlist_en ))
        enabled_en_  = enabled_en  or not bool(( enabled_en  ^ disabled_en ))
        disabled_en_ = disabled_en or not bool(( enabled_en  ^ disabled_en ))

        list_tasks(
            from_registry=registry_en_,
            from_cron=cronlist_en_,
            enabled=enabled_en_,
            disabled=disabled_en_
        )

        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1