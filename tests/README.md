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
- `mongoose state --init --json` reports and creates shared local state paths.
- `mongoose list` discovers available agents from `agent.json`.
- installing a missing agent fails and prints available agents.
- `mongoose install Njord` creates a user-local `Njord.cmd` launcher.
- the generated launcher calls the agent through `ask`.
- `mongoose uninstall Njord` removes the launcher.

The test uses `.test-localappdata-mongoose/` as a temporary local AppData substitute. That folder is ignored by Git.

## Mongoose State Validation

Script:

```text
tests/mongoose-state-validation.py
```

Run locally from the repository root:

```powershell
python .\tests\mongoose-state-validation.py
```

This test verifies:

- shared state directories are created under `%LOCALAPPDATA%\Agents`.
- atomic JSON writes round trip through the helper API.
- missing JSON files can return a caller-provided default.
- corrupted JSON raises an error that includes the file path.
- secret-like keys and log messages are redacted.
- expired JSONL log files are removed by retention cleanup.
- `mongoose state --init --json` reports the expected path contract.

The test uses `.test-localappdata-mongoose-state/` as a temporary local AppData substitute. That folder is ignored by Git.

## YNAB API Validation

Script:

```text
tests/ynab-api-validation.py
```

Run locally from the repository root:

```powershell
python .\tests\ynab-api-validation.py
```

This test verifies the read-only YNAB API foundation without calling the live API:

- plans, plan details, accounts, categories, months, transactions, and scheduled transactions parse from fixture responses.
- transaction query parameters normalize dates and optional filters.
- milliunit currency values and ISO dates normalize consistently.
- configured plan selection is deterministic.
- missing tokens, auth failures, 404s, rate limits, malformed JSON, URL errors, and timeouts return structured errors.
- error messages do not leak token-like details.
- malformed response shapes produce actionable messages.

## YNAB Config Validation

Script:

```text
tests/njord-config-validation.py
```

Run locally from the repository root:

```powershell
python .\tests\njord-config-validation.py
```

This test verifies Njord YNAB configuration handling without calling the live API:

- the preferred user-local config file can supply `YNAB_ACCESS_TOKEN` and `YNAB_BUDGET_ID`.
- missing tokens produce actionable status output.
- configured budget/plan IDs are validated against returned plans.
- installed-command style `Njord config status` routing works through `ask`.
- secret values are not printed in status output.

## Njord Snapshot Validation

Script:

```text
tests/njord-snapshot-validation.py
```

Run locally from the repository root:

```powershell
python .\tests\njord-snapshot-validation.py
```

This test verifies Njord's normalized financial snapshot model without calling the live API:

- accounts, category groups, categories, months, transactions, and scheduled transactions normalize from representative YNAB payloads.
- snapshot metadata includes source, selected plan, included resources, and freshness timestamp.
- summary helpers calculate open on-budget balance and underfunded categories from domain objects.
- snapshot serialization excludes raw payload fields and secret-like values.

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
- run `mongoose list` and discover `Njord`.
- run `mongoose install Njord` and create `Njord.cmd`.
- run `mongoose uninstall Njord` and remove `Njord.cmd`.
- run `mongoose update` against a local Git-backed registry URL and clone the registry.

The test uses `.test-localappdata-mongoose-exe/` and `.test-mongoose-update-registry/` as temporary folders. Both are ignored by Git.


