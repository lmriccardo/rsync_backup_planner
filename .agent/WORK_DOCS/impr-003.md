### Test Plan (copy‑paste)

Goal: add automated tests for core behavior without requiring external servers.

Perform this into another branch.

Scope

- Unit tests for parsing, plan generation, registry IO, log parsing.
- Integration tests using a local rsync daemon in CI.

Steps

1. Create tests/ and add unit tests:
    - tests/config_test.py: load valid/invalid YAML and assert validation errors.
    - tests/plan_test.py: load a target, generate plan JSON, assert command/log path.
    - tests/registry_test.py: read/write registry file in a temp dir.
    - tests/logs_test.py: parse sample log files (stdout/stderr/exit code).
2. Add CLI smoke tests (no network):
    - tests/cli_test.py: run python -m backupctl -h and inspect -h with subprocess.
3. Add integration test with local rsync daemon:
    - Use a temp dir and write rsyncd.conf + password file.
    - Start rsync --daemon --no-detach --config=... in the background.
    - Point config remote.host=127.0.0.1, remote.port=873.
    - Run backupctl validate and backupctl run --dry-run against it.
4. GitHub Actions:
    - Add job step to install rsync and start daemon for integration tests.
    - Run pytest -q.

Notes

- If rsync daemon setup is flaky, keep integration tests optional (e.g., -m integration).

Acceptance

- Unit tests pass on every PR.
- Integration tests pass on GH Actions without external services.