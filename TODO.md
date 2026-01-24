# TODO

---

## `backupctl` CLI Project

### Features

- [ ] **FEAT-001**: Implement `backupctl inspect <TARGET>` command
    + It inspects a registered target (config summary, notifications, command, status)
    + More description at [feat-001.md](.agent/WORK_DOCS/feat-001.md)

- [x] **FEAT-002**: Shows version tag when running `backupctl`

- [ ] **FEAT-003**: Webhook notifications
    + Add Webhook notifications for major platforms like discord and telegram
    + Leave it open for other platform as well (when supported)

### Enhancements

- [x] **IMPR-001**: Improve error handling with custom exceptions
    + Add exception specified-classes and remove `AssertionError` and `assert_1`

- [ ] **IMPR-002**: Improve console logging with rich text (colors and so on)

### Refactors

- [ ] **REF-001**: Migrate from REGISTRY txt to a SQLite database
    + Only one table named REGISTRY
    + Columns are: Target name, Schedule, Command, Status

### Actions

- [x] **ACT-001**: Release on tag push workflow
- [ ] **ACT-002**: Modify the `release-on-tag` workflow
    + Remove changelog collection
    + Adds PyPI package publishing using OpenID connect

### Miscellaneous

- [x] **MISC-001**: Modify the `pyproject.toml` file so that the python package
      is also installed using pip as a runnable script.

- [x] **MISC-002**: Create an `uninstall.sh` script

---
