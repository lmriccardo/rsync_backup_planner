# PR Checklist

## Scope & rules

- [ ] Change is scoped to the requested task.
- [ ] For NEW FEATURES: confirmed the feature exists in `TODO.md`.
- [ ] No files were modified outside this repository.
- [ ] No direct commits to `main` or protected branches.

## Structure

- [ ] New `backupctl` subcommand (if any) lives under `src/backupctl/<name>/` with `cmd.py` and `_core.py`.
- [ ] New models go in `src/backupctl/models/`.
- [ ] New utilities go in `src/backupctl/utils/`.
- [ ] No new files were added directly under `src/backupctl/` (folders used instead if needed).

## Config & schema

- [ ] YAML config remains consistent with `schemas/backup-config.schema.json`.
- [ ] If config semantics changed:
  - [ ] Updated `plan-config-example.yml`
  - [ ] Updated `backup-plan-example.json`
  - [ ] Re-generated schema using `scripts/create_json_schema.py` (if applicable)

## Quality

- [ ] Errors are handled cleanly (no raw tracebacks for expected failures).
- [ ] Code is readable, simple, and not over-engineered.
- [ ] Documentation updated where needed (README kept concise).

## Tests

- [ ] Relevant tests/checks were run (or noted that no tests exist yet).
- [ ] If tests were added: they live in `tests/` and follow `<name>_test.py`.
