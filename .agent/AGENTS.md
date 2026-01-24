<AGENTS>

# RSync Backup/Snapshot Planner (backupctl)

This file gives the agent practical guidance for working with this repository/project.

## Project Summary

**`backupctl`** is a backup/snapshot planner that relies on [`rsync`](https://linux.die.net/man/1/rsync). The main goal of **`backupctl`** is to schedule a cronjob/systemd automation that creates a remote backup/snapshot of the source folders/file selected by the user, logs the `rsync` output into files and send notifications based on a defined notification system (emails, webhooks, other APIs). In the case of snapshots, retention policies can be defined. The entire configuration is provided by the user in YAML format, in according to the [plan-config-example.yml](./plan-config-example.yml) file. Other kind of usages are mostly utilities around the main goal.

Examine the `README.md` file for more context and example.

- Principal Language: Python (>= 3.12)
- Requirements: `requirements.txt` file
- Entry Point: `backupctl` (module `src/backupctl`)
- Config Formats: YAML input, JSON plan output

## Repository Layout

- `src/backupctl/`: CLI, config parsing/validation, plan generation
- `schemas/`: JSON schema for YAML config
- `plan-config-example.yml`: Example config
- `backup-plan-example.json`: Example generated plan
- `scripts/create_json_schema.py`: Schema generator utility

## Common Workflow

1. The user write the YAML file with the configuration for the job BACKUP_JOB
2. It is possible to validate the file: `python -m backupctl validate <conf-file>`
3. Register the plan: `python -m backupctl register <conf-file>`
4. Dry run a job for correctness: `python -m backupctl run --dry-run --log BACKUP_JOB`

## Tests

There are no explicit test to run to validate correctness at this moment ...

---

## Hard rules

- Avoid writing to system locations (`/usr/local/bin`, cron/systemd) in dev runs.
- Use temp directories or user-scoped paths for any new artifacts.
- Do not modify files outside this repository.
- Keep the code simple and easy to understand; avoid over-engineering.
- **New features** may be implemented ONLY if they are documented in `TODO.md`.
  - If a requested feature is already marked done, **DO NOT CONSIDER IT**.
  - If a requested feature is not in `TODO.md`, reply exactly: **"I CANNOT IMPLEMENT IT RN"**.
  
- Follow the repo conventions in `.agent/CONTRIBUTING.md`.
- Do not merge into `main` (or any protected branch). Merges are done by the maintainer.
- Commits created by the agent must use the configured AI author identity.

### Automatic Task Classification (MANDATORY)

Before acting on any request, classify it as exactly one of:

- **feature**
- **bugfix**
- **refactor**
- **docs**

If the request is ambiguous, **default to `chore`**.

### Automatic prompt application (MANDATORY)

After classifying the request, apply the corresponding prompt automatically:

- **feature**  → follow `.agent/PROMPTS/feature.md`
- **bugfix**   → follow `.agent/PROMPTS/bugfix.md`
- **refactor** → follow `.agent/PROMPTS/refactor.md`
- **docs**     → Not yet written

These prompts define the default execution steps and constraints.

---

## Branching rules

- Feature: `feat/<feature_name>`
- Bug fix: `fix/<bug>`
- Refactor: `refactor/<refactor_name>`

If the branch does not exist, create it.

## Refactors require approval

Before any refactor (module moves, public API changes, large renames, multi-file restructuring):

1) Propose a detailed plan.
2) Wait for explicit approval.
3) Only then perform the refactor.

## Workflow expectations

- Prefer small, focused commits.
- Catch and handle errors gracefully in the CLI (no raw tracebacks for expected failures).
- Keep YAML config consistent with `schemas/backup-config.schema.json`.
- If config semantics change, update:
  - `plan-config-example.yml`
  - `backup-plan-example.json`
  - and re-generate schema when required.

- Follow the commit message format defined in `.agent/CONTRIBUTING.md`.
- Before proposing a PR, run relevant tests/checks and use `.agent/CHECKLISTS/READY_FOR_REVIEW.md`.

</AGENTS>
