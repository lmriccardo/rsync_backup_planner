# RSync Backup/Snapshot Planner

**`backupctl`** is a backup/snapshot planner that relies on [`rsync`](https://linux.die.net/man/1/rsync). `rsync` is a powerful command-line utility used to efficiently synchronize and transfer files between local and remote directories. It minimizes data transfer by using delta-transfer algorithm that only copies the specific portion of files that have changed.

The main goal of **`backupctl`** is to schedule a cronjob/systemd automation that creates a remote backup/snapshot of the source folders/file selected by the user, logs the `rsync` output into files and send notifications based on a defined notification system (emails, webhooks, other APIs). In the case of snapshots, retention policies can be defined. The entire configuration is provided by the user in YAML format, in according to the [plan-config-example.yml](./plan-config-example.yml) file. Other kind of usages are mostly utilities around the main goal.

Using the [create_json_schema.py](./create_json_schema.py) utility I have created a JSON Schema for the YAML file to helps editors to identify inconsistencies when ther user is writing the configuration. The resulting schema is **[backup-config.schema.json](./schemas/backup-config.schema.json)**

## Installation

The **recommended** way to install the **`backupctl`** command is using the `install.sh` script.

```bash
# Clone the repository
$ git clone https://github.com/lmriccardo/rsync_backup_planner.git
$ cd rsync_backup_planner

# Run the install.sh script
$ chmod u+x install.sh
$ ./install.sh --system
```

This will compile the python module into a single executable file using *PyInstaller* into the path `/usr/local/bin` folder. The python module *PyInstaller* if not found in the current python environment will be installed and uninstalled once the entire procedure ends.

Notice that this kind of installation is recommended but not required. You can install it in the way you want, but make sure that there will be at least an executable script into the `/usr/local/bin` folder named `backupctl`, otherwise any created `cronjob` will fail.

To uninstall, run the `uninstall.sh` script:

```bash
$ chmod u+x uninstall.sh
$ ./uninstall.sh --system
```

## Usage

```
$ backupctl -h

BACKUPCTL Version 0.1.0
usage: backupctl [-h] [--version]
                 {register,validate,status,remove,enable,disable,run,list,inspect}
                 ...

Backup control and consistency tool

positional arguments:
  {register,validate,status,remove,enable,disable,run,list,inspect}
    register            Create and register a new backup plan
    validate            Validate a user configuration
    status              High-level health check
    remove              Remove all or a list of specified jobs
    enable              Enable all or a list of specified jobs
    disable             Disable all or a list of specified jobs
    run                 Run a specified job
    list                List jobs in the registry or cronlist
    inspect             Inspect a registered target

options:
  -h, --help            show this help message and exit
  --version             Show version information
```

Check the installed version:

```
$ backupctl --version
BACKUPCTL Version <version>
```

This example will show just the main command `backupctl register`.

```
$ python -m backupctl register -h

usage: backupctl register [-h] [-v] config

positional arguments:
  config         Backup Plan configuration file

options:
  -h, --help     show this help message and exit
  -v, --verbose  Enable/Disable Verbosity
```

This command will register a backup plan (cronjob/systemd task) for each targets described in the configuration file. Write a YAML configuration file named `backup-plan.yml` like:

```yaml
# yaml-language-server: $schema=./schemas/backup-config.schema.json

backup:
  targets:
    simple_backup:
      remote:
        host: nas.domain
        user: admin
        password_file: .rsync_pass
        dest:
          module: backup
          folder: home
      rsync:
        excludes:
          - **/node_modules/*
          - **/.cache/*
          - **/cache/*
          - **/*.tmp
        sources:
          - /home/
      notification:
        email:
          from: user.email@gmail.com
          to:
            - user.email@gmail.com
          password: password
```

To quickly validate the configuration, you can:

```
$ backupctl validate backup-plan.yml
```

This will show any possible errors in the configuration. Once the configuration file has been created, run the command:

```
$ backupctl register backup-plan.yml -v
```

It will prints out some logs (with active verbosity) and on successful targets a JSON configuration is created in the default folder `$HOME/.backups/plans/` named `simple_backup-plan.json`. The format of the JSON is the same as [backup-plan-example.json](./backup-plan-example.json).

It is possible to give it a try using the `backupctl run` command.

```
$ backupctl run --log --notify simple_backup
```

> This is actual command that either cron or systemd will run

The command will generate a log file located in the folder `~/.backups/log/simple_backup/` named following the template `simple_backup-YYYYMMDD-HHMMSS.log`, and will also sends notifications back to the user if at least one notification system have been defined during configuration. 

## Contribution

You can fork this repo and contributes as you like. The python project can be installed locally as a python module using the `pip` command.

```bash
# Clone the repository
$ git clone https://github.com/lmriccardo/rsync_backup_planner.git
$ cd rsync_backup_planner

# First create a python virtual environment
$ python -m venv venv && source venv/bin/activate
$ pip install -U pip setuptools wheel
$ pip install -e .
```

This will install the python module in the current python environment. Now any command can be run as:

```
$ python -m backupctl COMMAND [OPTIONS...]
```
