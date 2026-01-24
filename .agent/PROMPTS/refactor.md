You are performin a REFACTOR.

Steps:

1. Create a detailed refactor plan that I have to accept it before continuing.
   If a project-related ID is provided, find the matching GitHub issue in the
   `Backupctl` project and read it.
        - The user is `lmriccardo` (owner of the project)
        - If GitHub cannot be accessed, ask the user for the issue URL or the full
          issue text (title + description), or a local file path that contains it.
        - Do not proceed without the issue details.

2. If the factor is non-trivial create the `refactor/<refactor-name>` branch
    - NON-TRIVIAL=Might need multiple steps of implementation and fixing bugs

3. Follow `.agent/CONTRIBUTING.md` for structure and conventions.
4. Apply the refactor
5. Update examples, docs, and config/schema if semantics change.
6. Run relevant tests/checks.
7. Verify `.agent/CHECKLISTS/READY_FOR_REVIEW.md`.
8. Summarize what was changed and what is ready for review.
