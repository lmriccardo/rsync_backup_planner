### Implement `backupctl inspect <options>` command

Command Syntax:

```
backupctl inspect <options>
```

where options are:

- `--target`: a list of targets to inspect (>= 1). If not given inspect all targets.

For each target shows the output with this format

```
Name      : <target_name>
Status    : <enabled/disabled> (with a green check/red cross)
Log Path  : <path/to/logfiles>
Schedule  : <schedule> (human-readable)
Last Run  : <date-time> (human-readable, u can take it from the log files)
Exit Code : <last-exit-code> (</path/to/last/logfile>)
Command   : <the-command-being-ran>
```

- There must be a clear separations between outputs for multiple targets.
- These information can be obtained from:
    + The log folder (path for the specific target is `~/.backups/log/<target-name>`)
    + The plan configuration JSON file ( path: `~/.backups/plans/<target-name>-plan.json` )
    + The registry file (path `~/.backups/REGISTRY`)

- These paths are listed into the `src/backupctl/constants.py` file with releated constants