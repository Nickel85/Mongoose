"""Mongoose CLI for installing and managing local agents."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


APP_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Agents" / "mongoose"
CONFIG_PATH = APP_ROOT / "config.json"
USER_BIN = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Agents" / "bin"
DEFAULT_REGISTRY_URL = "https://github.com/Nickel85/Agents.git"


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {
            "registryUrl": DEFAULT_REGISTRY_URL,
            "registryPath": str(APP_ROOT / "registry" / "Agents"),
        }

    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict[str, Any]) -> None:
    APP_ROOT.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def registry_path(config: dict[str, Any]) -> Path:
    return Path(config["registryPath"]).expanduser().resolve()


def agent_manifest_paths(root: Path) -> list[Path]:
    agents_root = root / "agents"
    if not agents_root.exists():
        return []

    manifests: list[Path] = []
    for child in sorted(agents_root.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue

        manifest = child / "agent.json"
        if manifest.exists():
            manifests.append(manifest)

    return manifests


def load_agent_registry(root: Path) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}

    for manifest_path in agent_manifest_paths(root):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        command_name = str(manifest.get("commandName", "")).strip()
        entrypoint_path = str(manifest.get("entrypointPath", "")).strip()
        if not command_name or not entrypoint_path:
            continue

        agent_dir = manifest_path.parent.resolve()
        entrypoint = (agent_dir / entrypoint_path).resolve()
        registry[command_name] = {
            "commandName": command_name,
            "displayName": manifest.get("displayName", command_name),
            "description": manifest.get("description", ""),
            "example": manifest.get("example", "Hello"),
            "entrypoint": str(entrypoint),
            "manifestPath": str(manifest_path.resolve()),
        }

    return registry


def ensure_registry(config: dict[str, Any]) -> Path:
    root = registry_path(config)
    if root.exists():
        return root

    registry_url = config.get("registryUrl", DEFAULT_REGISTRY_URL)
    root.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", registry_url, str(root)])
    return root


def run(command: list[str], cwd: Path | None = None) -> None:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def local_registry_source(registry_url: str) -> Path | None:
    path = Path(registry_url).expanduser()
    if path.exists():
        return path.resolve()

    parsed = urllib.parse.urlparse(registry_url)
    if parsed.scheme == "file":
        path = Path(urllib.request.url2pathname(parsed.path))
        return path if path.exists() else None

    if parsed.scheme:
        return None
    return None


def cmd_setup(args: argparse.Namespace) -> int:
    registry_root = Path(args.registry_root).expanduser().resolve()
    config = {
        "registryUrl": args.registry_url,
        "registryPath": str(registry_root),
    }
    save_config(config)
    USER_BIN.mkdir(parents=True, exist_ok=True)

    print("Mongoose configured.")
    print(f"Registry: {registry_root}")
    print(f"Config: {CONFIG_PATH}")
    print("")
    print("Try:")
    print("mongoose list")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    config = load_config()
    root = ensure_registry(config)
    agents = load_agent_registry(root)

    if not agents:
        print("No installable agents found.")
        return 0

    print("Available agents:")
    for command_name, agent in sorted(agents.items()):
        description = agent.get("description")
        if description:
            print(f"  {command_name} - {description}")
        else:
            print(f"  {command_name}")

    return 0


def create_agent_launcher(command_name: str, entrypoint: str) -> Path:
    USER_BIN.mkdir(parents=True, exist_ok=True)
    launcher_path = USER_BIN / f"{command_name}.cmd"
    launcher = f'@echo off\npython "{entrypoint}" ask %*\n'
    launcher_path.write_text(launcher, encoding="ascii")
    return launcher_path


def cmd_install(args: argparse.Namespace) -> int:
    config = load_config()
    root = ensure_registry(config)
    agents = load_agent_registry(root)
    agent = agents.get(args.agent)

    if agent is None:
        print(f"Agent '{args.agent}' does not exist.")
        print("")
        print("Available agents:")
        for command_name in sorted(agents):
            print(f"  {command_name}")
        return 1

    launcher_path = create_agent_launcher(agent["commandName"], agent["entrypoint"])
    print(f"Installed {agent['displayName']} as {agent['commandName']}.")
    print(f"Launcher: {launcher_path}")
    print("")
    print("Try:")
    print(f"{agent['commandName']} \"{agent.get('example', 'Hello')}\"")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    launcher_path = USER_BIN / f"{args.agent}.cmd"
    if not launcher_path.exists():
        print(f"Agent command '{args.agent}' is not installed.")
        return 0

    launcher_path.unlink()
    print(f"Removed {launcher_path}")
    return 0


def cmd_update(_: argparse.Namespace) -> int:
    config = load_config()
    root = registry_path(config)
    registry_url = config.get("registryUrl", DEFAULT_REGISTRY_URL)

    if root.exists() and (root / ".git").exists():
        run(["git", "pull", "--ff-only"], cwd=root)
        print(f"Updated registry at {root}")
        return 0

    if root.exists():
        print(f"Registry path exists but is not a Git repository: {root}")
        return 1

    root.parent.mkdir(parents=True, exist_ok=True)
    local_source = local_registry_source(registry_url)
    if local_source is not None:
        shutil.copytree(
            local_source,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        print(f"Copied local registry to {root}")
        return 0

    run(["git", "clone", registry_url, str(root)])
    print(f"Cloned registry to {root}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    examples = """examples:
  mongoose list
  mongoose install Nick
  mongoose uninstall Nick
  mongoose update
  mongoose setup --registry-root C:\\path\\to\\Agents

workflow:
  1. Run `mongoose list` to see available agents.
  2. Run `mongoose install <agent>` to install one as a command.
  3. Run the installed agent command, such as `Nick "Get me my latest budget"`.
  4. Run `mongoose update` to pull registry changes from GitHub.
"""
    parser = argparse.ArgumentParser(
        prog="mongoose",
        description="Install, list, uninstall, and update local agents.",
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser(
        "setup",
        help="Configure mongoose for an agent registry.",
        description="Configure mongoose with a local registry checkout and optional GitHub registry URL.",
    )
    setup.add_argument("--registry-root", required=True, help="Local registry checkout path.")
    setup.add_argument("--registry-url", default=DEFAULT_REGISTRY_URL, help="Git registry URL.")
    setup.set_defaults(handler=cmd_setup)

    list_parser = subparsers.add_parser(
        "list",
        aliases=["ls"],
        help="List available agents from the configured registry.",
        description="List installable agents discovered from agents/*/agent.json.",
    )
    list_parser.set_defaults(handler=cmd_list)

    install = subparsers.add_parser(
        "install",
        help="Install an agent as a user-local command.",
        description="Install an agent command into the user-local Agents bin directory.",
    )
    install.add_argument("agent", help="Agent commandName to install, such as Nick.")
    install.set_defaults(handler=cmd_install)

    uninstall = subparsers.add_parser(
        "uninstall",
        help="Uninstall a user-local agent command.",
        description="Remove an installed agent command from the user-local Agents bin directory.",
    )
    uninstall.add_argument("agent", help="Agent commandName to remove, such as Nick.")
    uninstall.set_defaults(handler=cmd_uninstall)

    update = subparsers.add_parser(
        "update",
        help="Pull down registry updates from GitHub.",
        description="Update the configured Git-backed registry with git pull --ff-only, or clone it if missing.",
    )
    update.set_defaults(handler=cmd_update)

    return parser


def main() -> int:
    configure_output()
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
