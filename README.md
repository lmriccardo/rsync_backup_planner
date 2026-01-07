# RSync Backup/Snapshot Planner

**`rbsched`** is a backup/snapshot planner that relies on [`rsync`](https://linux.die.net/man/1/rsync). `rsync` is a powerful command-line utility used to efficiently synchronize and transfer files between local and remote directories. It minimizes data transfer by using delta-transfer algorithm that only copies the specific portion of files that have changed.

**`rbsched`** schedules a cronjob/systemd automation that creates a remote backup/snapshot of the source folders/file selected by the user, logs the `rsync` output into files and send notifications based on a defined notification system (emails, webhoos, other APIs). In the case of snapshots, retention policies can be defined. The entire configuration is provided by the user in YAML format, in according to the [plan-config-example.yml](./plan-config-example.yml) file.

Using the [create_json_schema.py](./create_json_schema.py) utility I have created a JSON Schema for the YAML file to helps editors to identify inconsistencies when ther user is writing the configuration. The resulting schema is **[backup-config.schema.json](./schemas/backup-config.schema.json)**

## Usage

```
$ python create_backup_plan.py -h

usage: create_backup_plan.py [-h] [-v] config

positional arguments:
  config         Backup Plan configuration file

options:
  -h, --help     show this help message and exit
  -v, --verbose  Enable/Disable Verbosity
```

Write a YAML configuration file `backup-plan.yml`.

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

Once the configuration file has been created, run the command:

```
$ python create_backup_plan.py backup-plan.yml -v
```

It will prints out some logs (with active verbosity) and on successful targets a JSON configuration is created in the default folder `$HOME/.backups/plans/` named `simple_backup-plan.json`. The format of the JSON is the same as [backup-plan-example.json](./backup-plan-example.json).

It is possible to give it a try using the [scripts/run_backup.py](./scripts/run_backup.py) script.

```
$ python scripts/run_backup.py ~/.backups/plans/simple_backup-plan.json
```

> This is actual script that either cron or systemd will run

The script will generate a log file located in the folder `~/.backups/log/simple_backup/` named following the template `simple_backup-YYYYMMDD-HHMMSS.log`, and will also sends notifications back to the user if at least one notification system have been defined during configuration. 