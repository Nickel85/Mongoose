# Tests

This directory contains local validation scripts that are also run by GitHub Actions.

## GitHub Actions

The workflow lives at `.github/workflows/install-validation.yml`.

The mongoose package build workflow lives at `.github/workflows/mongoose-build.yml`.

The mongoose command smoke workflow lives at `.github/workflows/mongoose-smoke.yml`.

Install validation runs on:

- `push`
- `pull_request`

The mongoose build workflow runs on:

- pull requests targeting `main`
- pushes to `main`
- version tags matching `v*`

It uploads `dist/mongoose.exe` as an Actions artifact. On version tags, it also attaches `mongoose.exe` to the GitHub Release.

The mongoose smoke workflow runs on the same pull request, push, and tag triggers. It builds `mongoose.exe`, then smoke-tests `list`, `install`, `uninstall`, and `update`.

All workflows use `windows-latest` because the installer and executable are currently Windows-focused.

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
- `install/install-agent.ps1` exists.
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

## Mongoose Validation

Script:

```text
tests/mongoose-validation.ps1
```

Run locally from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\mongoose-validation.ps1
```

This test verifies:

- the Python-backed `mongoose` CLI exists.
- `mongoose setup` writes configuration against the local repo.
- `mongoose --help` includes install and update guidance.
- `mongoose list` discovers available agents from `agent.json`.
- installing a missing agent fails and prints available agents.
- `mongoose install Midas` creates a user-local `Midas.cmd` launcher.
- the generated launcher calls the agent through `ask`.
- `mongoose uninstall Midas` removes the launcher.

The test uses `.test-localappdata-mongoose/` as a temporary local AppData substitute. That folder is ignored by Git.

## Mongoose EXE Smoke

Script:

```text
tests/mongoose-exe-smoke.ps1
```

Run locally from the repository root after building `dist\mongoose.exe`:

```powershell
.\build-mongoose.cmd
powershell -ExecutionPolicy Bypass -File .\tests\mongoose-exe-smoke.ps1
```

This test verifies the built executable can:

- run `mongoose setup` against the local repo.
- run `mongoose list` and discover `Midas`.
- run `mongoose install Midas` and create `Midas.cmd`.
- run `mongoose uninstall Midas` and remove `Midas.cmd`.
- run `mongoose update` against a local Git-backed registry URL and clone the registry.

The test uses `.test-localappdata-mongoose-exe/` and `.test-mongoose-update-registry/` as temporary folders. Both are ignored by Git.

