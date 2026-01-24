### Version tag addition when running

- When the `backupctl` command is called (with any options) it needs to show the current version
- The version should be somewhat included into the program
    + It is either listed into the `pyproject.toml` file
    + or as the lastest git tag releated to the main branch

- At startup it also checks whether there are more recent version
    + YES -> Notify it to the user
    + NO  -> continue if nothing

- Adds also the `backupctl --version` command to shows the current version in this format

```
$ backupctl --version

BACKUPCTL Version <version>
<shows if there is any recent version>
```