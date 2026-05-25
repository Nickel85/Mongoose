# Agents

Repository of agents for personal use. Each agent is compartmentalized in its own directory with its own documentation, capabilities, configuration notes, and installation instructions.

## Agents

| Agent | Description | Documentation |
| --- | --- | --- |
| Midas | Personal finance agent for YNAB budget analysis, financial summaries, and future recommendations. | [agents/midas/README.md](agents/midas/README.md) |

## Structure

Each agent lives in its own directory under `agents/`. An agent directory should contain a `README.md` that explains the agent's purpose, operating notes, dependencies, and how to use it.

Capabilities for an agent live under that agent's `capabilities/` directory. Each capability gets its own folder with a `README.md` describing what it does, when to use it, inputs, outputs, and any important constraints.

Executable agents should expose an entrypoint script. The preferred filename is `agent.py` inside each agent's own directory, so many agents can safely have their own `agent.py`. The globally unique value is the `commandName` in `agent.json`, because that becomes the installed user-local command.

```text
agents/
  <agent-name>/
    agent.json
    agent.py
    README.md
    router.py
    config.py
    capabilities/
      <capability-name>/
        README.md
        <capability_program>.py
```

## Adding An Agent

1. Copy `agents/_template/` to `agents/<agent-name>/`.
2. Update the agent `README.md` with the agent's particulars.
3. Add capability folders under `agents/<agent-name>/capabilities/`.
4. Document each capability in its own `README.md`.
5. Add or update `agent.py` and `router.py` when capabilities should be callable from natural-language requests.
6. Add an `agent.json` manifest so the root installer can discover the agent. Its `commandName` must be unique across the repo.
7. Document installation from the agent's own `README.md`.

## Installing An Agent

The preferred installer is `mongoose`, the package-manager CLI for this repository.

Build and install it from the repository root:

```text
.\build-mongoose.cmd
.\install-mongoose.cmd
```

Then use:

```powershell
mongoose list
mongoose install Midas
mongoose uninstall Midas
mongoose update
```

`mongoose update` pulls down registry changes from the configured GitHub-backed registry.

The installer discovers installable agents by scanning `agents/*/agent.json`. Add that manifest when creating a new agent and it will appear in `mongoose list` automatically.

Each manifest's `entrypointPath` is resolved relative to that agent's directory. Multiple agents can use `agent.py`; they just cannot share the same `commandName`.

If the requested agent does not exist, the installer prints the available agent names.

Each agent README contains the agent-specific install name, configuration, examples, and any extra setup:

- [Midas install instructions](agents/midas/README.md)

Installers should not require administrator privileges. User-local command shims, configuration files, and secrets should stay scoped to the current user wherever possible.

See [mongoose/README.md](mongoose/README.md) for package-manager details.

## VS Code Setup

This repository includes workspace settings in `.vscode/`.

Recommended first step:

1. Open the repository in VS Code.
2. Install the recommended extensions when prompted.
3. Run the task `Create local .env`.
4. Add local secret values to `.env`.

The `.env` file is ignored by Git. Commit `.env.example` only.

## Testing

Tests live in `tests/` and are run by GitHub Actions on `push` and `pull_request`. See [tests/README.md](tests/README.md) for the current test list and local run instructions.

`mongoose.exe` is built by GitHub Actions for pull requests targeting `main`, pushes to `main`, and version tags. Pull request builds upload `mongoose.exe` as an Actions artifact, and version tag builds attach it to the GitHub Release.

GitHub Actions also smoke-tests the built executable by running `mongoose list`, `mongoose install`, `mongoose uninstall`, and `mongoose update`.

## Directory Guide

- `agents/`: All agent definitions.
- `agents/midas/`: Personal finance agent for analyzing YNAB budget data.
- `agents/midas/agent.json`: Install metadata for the `Midas` command.
- `agents/midas/agent.py`: Midas command-line entrypoint.
- `agents/midas/router.py`: Natural-language request router.
- `install.cmd`: One-file no-admin installer for installable agents.
- `install/`: User-local installer support scripts.
- `mongoose/`: Package-manager CLI and launcher source.
- `build-mongoose.cmd`: Builds `dist/mongoose.exe`.
- `install-mongoose.cmd`: Installs `mongoose.exe` as a user-local CLI.
- `tests/`: Local validation scripts also used by GitHub Actions.
- `agents/_template/`: Starter template for a new agent.
- `agents/_template/capabilities/_template/`: Starter template for a new capability.
