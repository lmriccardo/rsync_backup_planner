# TODO

---

## `backupctl` CLI Project

### Features

- [ ] FEAT-001: Implement `backupctl inspect <TARGET>` command
    + It inspects a registered target (config summary, notifications, command, status)

- [ ] FEAT-002: Webhook notifications
    + Add Webhook notifications for major platforms like discord and telegram
    + Leave it open for other platform as well (when supported)

### Enhancements

- [ ] IMPR-001: Improve error handling with custom exceptions
    + Add exception specified-classes and remove `AssertionError` and `assert_1`

- [ ] IMPR-002: Improve console logging with rich text (colors and so on)

### Actions

- [x] ACT-001: Release on tag push workflow

---
