You are implementing a BUG FIX.

Steps:
1. Identify the root cause of the bug. If a project-related ID is provided,
   find the matching GitHub issue in the `Backupctl` project and read it.
        - The user is `lmriccardo` (owner of the project)
        - If GitHub cannot be accessed, ask the user for the issue URL or the full
          issue text (title + description), or a local file path that contains it.
        - Do not proceed without the issue details.
        
2. Create a branch `fix/<bug_name>` if it does not exist.
3. Implement the minimal change required to fix the issue.
4. Add or update tests if appropriate.
5. Ensure errors are handled gracefully.
6. Run relevant tests/checks.
7. Verify `.agent/CHECKLISTS/READY_FOR_REVIEW.md`.
8. Summarize the fix and its impact.
