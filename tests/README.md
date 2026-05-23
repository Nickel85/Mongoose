# Tests

This directory contains local validation scripts that are also run by GitHub Actions.

## GitHub Actions

The workflow lives at `.github/workflows/install-validation.yml`.

It runs on:

- `push`
- `pull_request`

The workflow uses `windows-latest` because the installer is currently Windows-focused.

## Install Validation

Script:

```text
tests/install-validation.ps1
```

Run locally from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\install-validation.ps1
```

This test verifies:

- `install.cmd` exists.
- `install/install-nick.ps1` exists.
- every real agent directory has an `agent.json`.
- template directories beginning with `_` are ignored.
- each manifest has `commandName`, `displayName`, `entrypointPath`, `example`, and `description`.
- `commandName` values are valid command names.
- `commandName` values are unique across all agents.
- `entrypointPath` is relative, not absolute.
- `entrypointPath` resolves to an existing file.
- `entrypointPath` stays inside its own agent directory.
- unknown agents fail and print available agents.
- known agents install into a user-local test bin directory.
- generated launchers call the configured entrypoint and the `ask` command.

The test uses `.test-localappdata/` as a temporary local AppData substitute. That folder is ignored by Git.

