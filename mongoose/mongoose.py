"""Mongoose CLI for installing and managing local agents."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


AGENTS_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Agents"
APP_ROOT = AGENTS_ROOT / "mongoose"
CONFIG_PATH = APP_ROOT / "config.json"
USER_BIN = AGENTS_ROOT / "bin"
STATE_ROOT = AGENTS_ROOT / "state"
LOG_ROOT = AGENTS_ROOT / "logs"
JOBS_ROOT = STATE_ROOT / "jobs"
AGENT_STATE_ROOT = STATE_ROOT / "agents"
NON_SECRET_CONFIG_ROOT = STATE_ROOT / "config"
DEFAULT_REGISTRY_URL = "https://github.com/Nickel85/Agents.git"
DEFAULT_LOG_RETENTION_DAYS = 30
SECRET_KEYWORDS = (
    "access_token",
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
)
SECRET_TEXT_PATTERN = re.compile(
    r"(?i)\b(access_token|api_key|authorization|password|secret|token)\s*[:=]\s*([^\s,;]+)"
)


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

    return read_json(CONFIG_PATH)


def save_config(config: dict[str, Any]) -> None:
    write_json_atomic(CONFIG_PATH, config)


def state_contract() -> dict[str, str]:
    return {
        "root": str(AGENTS_ROOT),
        "bin": str(USER_BIN),
        "mongoose": str(APP_ROOT),
        "mongooseConfig": str(CONFIG_PATH),
        "registry": str(APP_ROOT / "registry" / "Agents"),
        "state": str(STATE_ROOT),
        "nonSecretConfig": str(NON_SECRET_CONFIG_ROOT),
        "agentState": str(AGENT_STATE_ROOT),
        "jobs": str(JOBS_ROOT),
        "logs": str(LOG_ROOT),
    }


def ensure_state_layout() -> dict[str, str]:
    paths = state_contract()
    for key, value in paths.items():
        path = Path(value)
        if key == "mongooseConfig":
            path.parent.mkdir(parents=True, exist_ok=True)
        elif key == "registry":
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
    return paths


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_text(content, encoding=encoding)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not read JSON file: {path}") from exc


def write_json_atomic(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(keyword in normalized for keyword in SECRET_KEYWORDS)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if is_secret_key(str(key)) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def redact_secret_text(message: str) -> str:
    return SECRET_TEXT_PATTERN.sub(lambda match: f"{match.group(1)}=[redacted]", message)


def append_log(component: str, message: str, level: str = "INFO", **metadata: Any) -> Path:
    ensure_state_layout()
    safe_component = re.sub(r"[^A-Za-z0-9_.-]+", "-", component).strip(".-") or "mongoose"
    log_path = LOG_ROOT / f"{safe_component}.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "component": safe_component,
        "message": redact_secret_text(message),
    }
    if metadata:
        record["metadata"] = redact_secrets(metadata)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True) + "\n")
    return log_path


def cleanup_logs(retention_days: int = DEFAULT_LOG_RETENTION_DAYS) -> list[Path]:
    if retention_days < 0:
        raise ValueError("retention_days must be zero or greater")
    if not LOG_ROOT.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed: list[Path] = []
    for log_path in LOG_ROOT.glob("*.jsonl"):
        modified = datetime.fromtimestamp(log_path.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            log_path.unlink()
            removed.append(log_path)
    return removed


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
    ensure_state_layout()
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


def cmd_state(args: argparse.Namespace) -> int:
    paths = ensure_state_layout() if args.init else state_contract()
    if args.cleanup_logs:
        removed = cleanup_logs(args.log_retention_days)
        print(f"Removed {len(removed)} expired log file(s).")
        print("")

    if args.json:
        print(json.dumps(paths, indent=2, sort_keys=True))
        return 0

    print("Mongoose local state:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
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
  mongoose install Njord
  mongoose uninstall Njord
  mongoose update
  mongoose state --init
  mongoose setup --registry-root C:\\path\\to\\Agents

workflow:
  1. Run `mongoose list` to see available agents.
  2. Run `mongoose install <agent>` to install one as a command.
  3. Run the installed agent command, such as `Njord "Get me my latest budget"`.
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

    state = subparsers.add_parser(
        "state",
        help="Show or initialize local Mongoose state paths.",
        description="Show the shared user-local state, config, job, and log paths used by Mongoose.",
    )
    state.add_argument("--init", action="store_true", help="Create the local state directory layout.")
    state.add_argument("--json", action="store_true", help="Print paths as JSON.")
    state.add_argument(
        "--cleanup-logs",
        action="store_true",
        help="Remove JSONL log files older than the retention period.",
    )
    state.add_argument(
        "--log-retention-days",
        type=int,
        default=DEFAULT_LOG_RETENTION_DAYS,
        help="Number of days of logs to keep when --cleanup-logs is used.",
    )
    state.set_defaults(handler=cmd_state)

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
    install.add_argument("agent", help="Agent commandName to install, such as Njord.")
    install.set_defaults(handler=cmd_install)

    uninstall = subparsers.add_parser(
        "uninstall",
        help="Uninstall a user-local agent command.",
        description="Remove an installed agent command from the user-local Agents bin directory.",
    )
    uninstall.add_argument("agent", help="Agent commandName to remove, such as Njord.")
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
    try:
        return args.handler(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

