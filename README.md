# Agents

Repository of installable agents and the local tooling used to manage them.
Each agent is compartmentalized in its own directory with its own
documentation, capabilities, configuration notes, and installation
instructions.

Today, this repository contains one concrete agent, Njord, and Mongoose, the
local package-manager CLI used to install, inspect, route to, and run agents
from this repository.

## Mongoose Vision

Mongoose is being developed toward a local-first runtime and package manager
for AI agents that enables agents to be installed, configured, discovered, and
executed consistently across different environments.

The current CLI already supports local agent installation, manifest validation,
capability discovery, deterministic routing, user-local state, and installed
agent execution. The broader platform vision is that agents declare the
capabilities they require, such as LLMs, memory, tools, storage, and configured
APIs, and Mongoose provides those capabilities through common interfaces. That
would allow the same agent to run on a personal laptop, enterprise workstation,
or server without modification.

That full runtime surface is roadmap work, not current behavior. The active
roadmap tracks:

- provider-neutral LLM runtime support in [#23](https://github.com/Nickel85/Agents/issues/23)
- persistent scheduling and jobs in [#1](https://github.com/Nickel85/Agents/issues/1), [#2](https://github.com/Nickel85/Agents/issues/2), [#4](https://github.com/Nickel85/Agents/issues/4), and [#5](https://github.com/Nickel85/Agents/issues/5)
- cross-platform runtime support in [#38](https://github.com/Nickel85/Agents/issues/38)
- dependency and environment isolation in [#39](https://github.com/Nickel85/Agents/issues/39)
- package registry and versioning in [#40](https://github.com/Nickel85/Agents/issues/40)
- portable agent execution contracts in [#41](https://github.com/Nickel85/Agents/issues/41)
- common memory, storage, tool, and API provider interfaces in [#42](https://github.com/Nickel85/Agents/issues/42)

Mongoose platform milestones and Njord agent-value milestones are intentionally
sequenced separately. Njord is the first concrete use case and should prove
useful deterministic finance workflows before the platform grows package,
runtime, and provider abstractions beyond what real agents need.

## Agents

| Agent | Description | Documentation |
| --- | --- | --- |
| Njord | First concrete Mongoose-managed agent; personal finance analysis for YNAB budget data, financial summaries, and future recommendations. | [agents/njord/README.md](agents/njord/README.md) |

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
mongoose install Njord
mongoose show Njord
mongoose capabilities
mongoose route --task-type budget-summary "current budget"
mongoose run Njord config status
mongoose remove Njord
mongoose update
```

`mongoose update` pulls down registry changes from the configured GitHub-backed registry.

Mongoose discovers installable agents by scanning `agents/*/agent.json`. Add that manifest when creating a new agent and it will appear in `mongoose list` automatically.

Each manifest's `entrypointPath` is resolved relative to that agent's directory. Multiple agents can use `agent.py`; they just cannot share the same `commandName`.

Installed agent metadata is stored under `%LOCALAPPDATA%\Agents\state\agents`. Removing an agent deletes the local command shim and installed metadata, not the source package.

If the requested agent does not exist, Mongoose prints the available agent names.

Manifests can also declare capability metadata, supported task types, configuration requirements, compatibility constraints, and optional LLM needs. Mongoose reads that metadata without importing agent code:

```powershell
mongoose validate
mongoose show Njord
mongoose capabilities
```

Once agents are installed, Mongoose can route requests across declared capabilities with deterministic task-type matching:

```powershell
mongoose route --task-type budget-summary "current budget"
```

Secrets do not belong in manifests. Manifests should reference configuration names such as `YNAB_ACCESS_TOKEN`; actual tokens stay in environment variables, user-local config, or future Mongoose secret/profile storage.

Each agent README contains the agent-specific install name, configuration, examples, and any extra setup:

- [Njord install instructions](agents/njord/README.md)

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
- `agents/njord/`: Personal finance agent for analyzing YNAB budget data.
- `agents/njord/agent.json`: Install metadata for the `Njord` command.
- `agents/njord/agent.py`: Njord command-line entrypoint.
- `agents/njord/router.py`: Natural-language request router.
- `install.cmd`: One-file no-admin installer for installable agents.
- `install/`: User-local installer support scripts.
- `mongoose/`: Package-manager CLI and launcher source.
- `build-mongoose.cmd`: Builds `dist/mongoose.exe`.
- `install-mongoose.cmd`: Installs `mongoose.exe` as a user-local CLI.
- `tests/`: Local validation scripts also used by GitHub Actions.
- `agents/_template/`: Starter template for a new agent.
- `agents/_template/capabilities/_template/`: Starter template for a new capability.

