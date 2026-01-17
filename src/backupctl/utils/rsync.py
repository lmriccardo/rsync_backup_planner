import subprocess
from typing import List, Optional, Any, Mapping, overload
from backupctl.models.rsync import *

def get_model_from_opts(*, opts: Optional[object] = None, **kwargs: Any) -> RSyncOptionsModel:
    if opts is not None and kwargs:
        raise TypeError("Pass either a single ops object/dict OR kwargs, not both")
    
    model = None # This is the model with rsync options
    data = None  # Dict with rsync options from opts
    
    if opts is None: data = kwargs
    if isinstance(opts, Mapping): data = dict(opts)
    if isinstance(opts, RSyncOptionsModel):
        model = opts
        return model
    
    if data is None and model is None:
        # None of the two was set but opts has been given ... Problem
        TypeError("opts must be a RSyncOptionsModel or a mapping")

    # If the data were passed as options of kwards
    if opts is None or isinstance(opts, Mapping):
        model = RSyncOptionsModel(**data)

    return model

@overload
def create_rsync_command(opts: RSyncOptionsModel) -> List[str]: ...
@overload
def create_rsync_command(opts: Mapping[str, Any]) -> List[str]: ...
@overload
def create_rsync_command(**kwargs: Any) -> List[str]: ...

def create_rsync_command(*, opts: Optional[object] = None, **kwargs: Any) -> List[str]:
    """ Format the rsync command as list of parts from options """
    opts = get_model_from_opts(opts=opts, **kwargs)

    command = ["rsync"]

    if opts.use_flags: command += ["-avvHAX"] if opts.verbose else ["-aHAX"]
    if opts.list_only: command += ["--list-only"]
    if opts.password_file: command += [f"--password-file={opts.password_file}"]
    if opts.dry_run: command += ["--dry-run"]
    if opts.delete: command += ["--delete"] + [ f"--delete-{opts.delete.value}" ]
    if opts.progress: command += ["--info=progress2"]
    if opts.prune_empty_dirs: command += ["--prune-empty-dirs"]
    if len(opts.includes) > 0:
        for include in opts.includes:
            command += [f"--include={include}"]
    
    if len(opts.excludes) > 0:
        for exclude in opts.excludes:
            command += [f"--exclude={exclude}"]

    if opts.exclude_from: command += [f"--exclude-from={opts.exclude_from}"]
    if opts.numeric_ids: command += ["--numeric-ids"]
    if opts.itemize_changes: command += ["--itemize-changes"]

    # Add the sources
    if opts.sources: command.extend(opts.sources)

    # Add the host, port, user, module and folder
    rsync_user = "" if not opts.user else f"{opts.user}@"
    rsync_host = f"rsync://{rsync_user}{opts.host}:{opts.port}/"
    if opts.module: rsync_host += f"{opts.module}/"
    if opts.folder: rsync_host += f"{opts.folder}/"
    command += [rsync_host]

    return command

@overload
def run_rsync_command(opts: RSyncOptionsModel) -> RSyncOutput: ...
@overload
def run_rsync_command(opts: Mapping[str, Any]) -> RSyncOutput: ...
@overload
def run_rsync_command(**kwargs: Any) -> RSyncOutput: ...

def run_rsync_command(*, opts: Optional[object] = None, **kwargs: Any) -> RSyncOutput:
    """ Run an Rsync command and retursn the formatted output """
    model = get_model_from_opts(opts=opts, **kwargs)
    command = create_rsync_command(opts=model) # Create the running command
    output = subprocess.run(command, capture_output=True, text=True, check=False)
    return RSyncOutput.from_cmd_out(output)