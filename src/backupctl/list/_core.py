from backupctl.models.registry import read_registry
from backupctl.utils.cron import read_cronlist_jobs
from tabulate import tabulate
from typing import List

def _add_task_item( l: List[List[str]], name: str, cmd: str, enabled: bool ) -> None:
    """ Add the input item task into the task list """
    l.append(
        [ name, cmd, "✅ (ENABLED)" if enabled else "❌ (DISABLED)" ]
    )

def _print_task_list( l: List[List[str]], *, title: str|None=None ) -> None:
    """ Print the task list using Tabulate """
    headers = ["Name", "Command", "Status"]
    t = tabulate( l, headers=headers, tablefmt="grid" )
    
    if title is not None:
        t_len = len(t.split("\n")[0])
        title_len = len(title)
        rpad_size = (t_len - title_len) // 2
        lpad_size = ( t_len - title_len ) - rpad_size
        title = " " * lpad_size + title + " " * rpad_size
        print(title)

    print(t)

def print_registry( enabled: bool, disabled: bool ) -> None:
    """ Print the tasks from the registry """
    registry = read_registry()
    if not registry:
        print("[*] The registry is empty")
        return
    
    task_list = []
    for _, task in registry.items():
        task_en = task.is_enabled()
        if ( (task_en and enabled) or (not task_en and disabled) ):
            _add_task_item(task_list, task.name, 
                task.cmd, task_en)
    
    if ( len(task_list) == 0 ):
        print("[*] Nothing to print for the registry")
        return

    _print_task_list( task_list, title="REGISTRY" )

def print_cron( enabled: bool, disabled: bool ):
    """ Print the task from the cronlist """
    cronlist = read_cronlist_jobs()
    if not cronlist:
        print("[*] The crontab is empty")
        return
    
    task_list = []
    for task_name, ( task_en, task_cmd ) in cronlist.items():
        if ( (task_en and enabled) or (not task_en and disabled) ):
            _add_task_item( task_list, task_name,
                task_cmd, task_en)
    
    if ( len(task_list) == 0 ):
        print("[*] Nothing to print for the cronlist")
        return

    _print_task_list( task_list, title="CRONLIST" )

def list_tasks( *, from_registry: bool=True, from_cron: bool=True,
    enabled: bool=True, disabled: bool=True
) -> None:
    # Print from the registry if enabled
    if from_registry:
        print()
        print_registry(enabled, disabled)

    if from_cron: 
        print()
        print_cron(enabled, disabled)
    
    print()