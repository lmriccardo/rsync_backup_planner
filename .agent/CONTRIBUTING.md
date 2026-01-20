# Development Information

This document defines development best practices for features, refactors, bug fixes, and general contributions
(including AI agents). It also defines branch naming conventions and project structure rules.

## Gate for new features

- You can implement a **new feature** only if it is documented in `TODO.md`.
- If it is not documented there, reply exactly: **"I CANNOT IMPLEMENT IT RN"**.

> Note: Bug fixes, docs, and small maintenance changes may proceed if they are clearly requested/scoped.

## General information

- To run `backupctl` via Python, use the virtual environment `venv` and run:
  - `python -m backupctl <COMMAND>`

- Add helper scripts to the repository `scripts/` folder.
- Add Python dependencies to `requirements.txt`.
- Add installation/setup configuration to `pyproject.toml`.
- Keep `README.md` useful and not overly verbose: simple, self-explanatory, and practical.
- Do not over-engineer. Prefer straightforward, readable code.
- If examples are needed to validate a feature, add them under:
  - `example/<feature_name>/` (create the folder if missing)

- **DO NOT go outside this project environment.**
- Keep code documented, but not excessively verbose.

## Feature implementation (CLI / subcommands)

- Any new subcommand for `backupctl` must have its own Python submodule under: `src/backupctl/<subcommand_name>/`
- Each subcommand module must contain:
  1) `cmd.py` — entry point for CLI execution
  2) `_core.py` — implementation / logic
  3) Additional files only if required and they do not fit existing folders

### Config schema changes

- If a feature changes the structure/semantics of the input configuration, re-generate the JSON schema by running:
  - `python scripts/create_json_schema.py --root <PY_ROOT_OBJECT> -o <OUTPUT.json> <SCHEMA>.py`

- The script generates JSON schema from a Python file containing a Pydantic root model/class.

### Project structure rules

- New models / dataclasses / similar go in `src/backupctl/models/`
- Generic utilities go in `src/backupctl/utils/`
- **Do not add additional files directly under `src/backupctl/`**; Add a folder instead if needed.
- Keep YAML config shape consistent with `schemas/backup-config.schema.json`
- When changing config semantics, update `plan-config-example.yml` and `backup-plan-example.json`
- Prefer small, focused functions for CLI subcommands.

### Error handling

- Do not let raw exceptions bubble to the CLI for expected/handled error cases.
- Catch errors, print a clean and helpful message, and exit gracefully.
- Prefer typed/custom exceptions in core logic if helpful, but ensure the CLI output remains user-friendly.

## Refactoring

- Before any refactoring, provide a detailed plan describing:
  - What will change
  - Why it is needed
  - Which modules/files will be touched
  - Risk/rollback considerations

- Proceed ONLY after explicit approval.
- After refactoring, re-run all tests (if any exist).

## Tests

- If adding tests, create a folder at repo root `tests/`
- Test filename format: `<test-name>_test.py`

> Add the command(s) to run tests here once your test runner is decided (e.g. `pytest -q`).
> Until then, run only the relevant checks for the changed area, and avoid claiming tests passed if none exist.

## Commit message format (MANDATORY)

Commits must follow this format:

`<type>(<scope>): <short description>`

Where:
- `<type>` is one of:
  - feat     (new feature)
  - fix      (bug fix)
  - refactor (code restructuring without behavior change)
  - docs     (documentation only)
  - chore    (maintenance, tooling, formatting)
- `<scope>` is optional but recommended (e.g. config, cli, schema).
- Description:
  - imperative mood
  - present tense
  - no trailing period
  - concise (max ~72 chars)

When committing you MUST change the committer as

- name: Codex
- email: codex@agent.noreply.github.com

### Examples

- `feat(cli): add inspect subcommand`
- `fix(config): handle missing targets key`
- `refactor(schema): simplify validation logic`
- `docs(readme): document inspect command`
