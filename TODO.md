# TODO

---

## `backupctl` CLI Project

### Features

- [x] **FEAT-001**: Implement `backupctl inspect <TARGET>` command
- [x] **FEAT-002**: Shows version tag when running `backupctl`

- [ ] **FEAT-003**: Webhook notifications
    + Add Webhook notifications for major platforms like discord and telegram
    + Leave it open for other platform as well (when supported)

### Enhancements

- [x] **IMPR-001**: Improve error handling with custom exceptions
- [ ] **IMPR-002**: Improve console logging with rich text (colors and so on)
- [x] **IMPR-003**: Add tests for backupctl

### Refactors

- [ ] **REF-001**: Migrate from REGISTRY txt to a SQLite database
    + Only one table named REGISTRY
    + Columns are: Target name, Schedule, Command, Status

- [ ] **REF-002**: Refactors overall package structure
    + Mode Details in [ref-002.md](./.agent/WORK_DOCS/ref-002.md)

### Actions

- [x] **ACT-001**: Release on tag push workflow
- [x] **ACT-002**: Modify the `release-on-tag` workflow
- [x] **ACT-003**: `release-on-tag` also ship a `.deb` package

### Miscellaneous

- [x] **MISC-001**: Modify the `pyproject.toml` to install a runnable script.
- [x] **MISC-002**: Create an `uninstall.sh` script

---
