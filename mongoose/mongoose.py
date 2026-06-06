"""Mongoose CLI for managing local agent capabilities."""

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
DEFAULT_REGISTRY_URL = "https://github.com/Nickel85/Mongoose.git"
DEFAULT_LOG_RETENTION_DAYS = 30
MONGOOSE_RELEASES_API_URL = "https://api.github.com/repos/Nickel85/Mongoose/releases"
MONGOOSE_RELEASE_ASSET_NAME = "mongoose.exe"
MONGOOSE_VERSION = "0.1.2"
MONGOOSE_RELEASE_KIND = "development"
MONGOOSE_RELEASE_TAG = ""
# Increment only for breaking manifest contract changes. Additive optional metadata stays on the same version.
SUPPORTED_MANIFEST_SCHEMA_VERSION = 1
COMMAND_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
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
MANIFEST_SECRET_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "password",
    "secret",
    "token",
}
ANSI_RESET = "\033[0m"
ANSI_STYLES = {
    "heading": "\033[36;1m",
    "success": "\033[32;1m",
    "warning": "\033[33;1m",
    "error": "\033[31;1m",
    "muted": "\033[2m",
    "selected": "\033[34;1m",
}
OUTPUT_COLOR_ENABLED = False


class ManifestValidationError(ValueError):
    def __init__(self, manifest_path: Path, errors: list[str]) -> None:
        self.manifest_path = manifest_path
        self.errors = errors
        super().__init__(self.format_message())

    def format_message(self) -> str:
        lines = [f"Invalid agent manifest: {self.manifest_path}"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


class SelfUpdateError(RuntimeError):
    pass


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def color_requested_by_env() -> bool:
    value = os.environ.get("MONGOOSE_FORCE_COLOR", "")
    return value.strip().lower() in {"1", "true", "yes", "always"}


def color_disabled_by_env() -> bool:
    disabled_values = {
        os.environ.get("NO_COLOR", ""),
        os.environ.get("MONGOOSE_NO_COLOR", ""),
    }
    if any(value is not None and str(value).strip() for value in disabled_values):
        return True
    color_mode = os.environ.get("MONGOOSE_COLOR", "").strip().lower()
    return color_mode in {"0", "false", "never", "no"}


def should_use_color(no_color: bool = False) -> bool:
    if no_color or color_disabled_by_env():
        return False
    return color_requested_by_env() or sys.stdout.isatty()


def set_output_color(enabled: bool) -> None:
    global OUTPUT_COLOR_ENABLED
    OUTPUT_COLOR_ENABLED = enabled


def styled(text: str, style: str) -> str:
    if not OUTPUT_COLOR_ENABLED:
        return text
    prefix = ANSI_STYLES.get(style)
    if not prefix:
        return text
    return f"{prefix}{text}{ANSI_RESET}"


def print_heading(text: str) -> None:
    print(styled(text, "heading"))


def print_success(text: str) -> None:
    print(styled(text, "success"))


def print_warning(text: str) -> None:
    print(styled(text, "warning"))


def print_error(text: str, *, file: Any | None = None) -> None:
    print(styled(text, "error"), file=file or sys.stdout)


def print_muted(text: str) -> None:
    print(styled(text, "muted"))


def label_line(label: str, value: Any, style: str = "selected") -> str:
    return f"{styled(label + ':', style)} {value}"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {
            "registryUrl": DEFAULT_REGISTRY_URL,
            "registryPath": str(APP_ROOT / "registry" / "Mongoose"),
        }

    return read_json(CONFIG_PATH)


def save_config(config: dict[str, Any]) -> None:
    write_json_atomic(CONFIG_PATH, config)


def state_contract() -> dict[str, str]:
    config = load_config()
    registry = registry_path(config)
    paths = {
        "version": MONGOOSE_VERSION,
        "releaseKind": MONGOOSE_RELEASE_KIND,
        "releaseTag": MONGOOSE_RELEASE_TAG,
        "cliSource": str(Path(__file__).resolve()),
        "root": str(AGENTS_ROOT),
        "bin": str(USER_BIN),
        "mongoose": str(APP_ROOT),
        "mongooseConfig": str(CONFIG_PATH),
        "registry": str(registry),
        "registryUrl": str(config.get("registryUrl", DEFAULT_REGISTRY_URL)),
        "registryRevision": registry_revision(registry),
        "registryStatus": registry_status(registry),
        "state": str(STATE_ROOT),
        "nonSecretConfig": str(NON_SECRET_CONFIG_ROOT),
        "agentState": str(AGENT_STATE_ROOT),
        "jobs": str(JOBS_ROOT),
        "logs": str(LOG_ROOT),
    }
    return paths


def ensure_state_layout() -> dict[str, str]:
    paths = state_contract()
    directory_keys = {
        "root",
        "bin",
        "mongoose",
        "state",
        "nonSecretConfig",
        "agentState",
        "jobs",
        "logs",
    }
    for key, value in paths.items():
        path = Path(value)
        if key == "mongooseConfig":
            path.parent.mkdir(parents=True, exist_ok=True)
        elif key == "registry":
            path.parent.mkdir(parents=True, exist_ok=True)
        elif key in directory_keys:
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


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in list_value(value) if str(item).strip()]


def manifest_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in MANIFEST_SECRET_KEYS


def find_manifest_secret_values(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            if manifest_secret_key(str(key)) and str(item).strip():
                errors.append(f"{item_path} must not contain a secret value.")
            errors.extend(find_manifest_secret_values(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(find_manifest_secret_values(item, f"{path}[{index}]"))
    return errors


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> None:
    errors: list[str] = []

    required_string_fields = (
        "commandName",
        "displayName",
        "entrypointPath",
        "example",
        "description",
    )
    for field_name in required_string_fields:
        if not str(manifest.get(field_name, "")).strip():
            errors.append(f"Missing required string field: {field_name}")

    command_name = str(manifest.get("commandName", "")).strip()
    if command_name and not COMMAND_NAME_PATTERN.match(command_name):
        errors.append("commandName must start with a letter and contain only letters, numbers, '_' or '-'.")

    schema_version = manifest.get("schemaVersion", SUPPORTED_MANIFEST_SCHEMA_VERSION)
    if not isinstance(schema_version, int):
        errors.append("schemaVersion must be an integer when present.")
    elif schema_version > SUPPORTED_MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"schemaVersion {schema_version} is newer than supported version {SUPPORTED_MANIFEST_SCHEMA_VERSION}."
        )

    agent_dir = manifest_path.parent
    entrypoint_path = str(manifest.get("entrypointPath", "")).strip()
    if entrypoint_path:
        if Path(entrypoint_path).is_absolute():
            errors.append("entrypointPath must be relative to the agent directory.")
        elif not (agent_dir / entrypoint_path).exists():
            errors.append(f"entrypointPath does not exist: {entrypoint_path}")

    identity = manifest.get("identity", {})
    if identity and not isinstance(identity, dict):
        errors.append("identity must be an object when present.")

    entrypoints = manifest.get("entrypoints", {})
    if entrypoints and not isinstance(entrypoints, dict):
        errors.append("entrypoints must be an object when present.")
    elif isinstance(entrypoints, dict):
        for name, relative_path in entrypoints.items():
            relative = str(relative_path).strip()
            if not relative:
                errors.append(f"entrypoints.{name} must be a non-empty path.")
            elif Path(relative).is_absolute():
                errors.append(f"entrypoints.{name} must be relative to the agent directory.")
            elif not (agent_dir / relative).exists():
                errors.append(f"entrypoints.{name} does not exist: {relative}")

    capabilities = manifest.get("capabilities", [])
    if capabilities and not isinstance(capabilities, list):
        errors.append("capabilities must be a list when present.")
    elif isinstance(capabilities, list):
        capability_names: set[str] = set()
        for index, capability in enumerate(capabilities):
            prefix = f"capabilities[{index}]"
            if not isinstance(capability, dict):
                errors.append(f"{prefix} must be an object.")
                continue

            name = str(capability.get("name", "")).strip()
            if not name:
                errors.append(f"{prefix}.name is required.")
            elif name in capability_names:
                errors.append(f"{prefix}.name duplicates capability '{name}'.")
            else:
                capability_names.add(name)

            if not str(capability.get("description", "")).strip():
                errors.append(f"{prefix}.description is required.")

            if capability.get("taskTypes") is not None and not isinstance(capability.get("taskTypes"), list):
                errors.append(f"{prefix}.taskTypes must be a list.")

            if capability.get("requiredInputs") is not None and not isinstance(capability.get("requiredInputs"), list):
                errors.append(f"{prefix}.requiredInputs must be a list.")

            config = capability.get("configuration", capability.get("config", {}))
            if config and not isinstance(config, dict):
                errors.append(f"{prefix}.configuration must be an object.")

            llm = capability.get("llm", {})
            if llm and not isinstance(llm, dict):
                errors.append(f"{prefix}.llm must be an object.")
            elif isinstance(llm, dict):
                mode = str(llm.get("mode", "none")).strip()
                if mode and mode not in {"none", "optional", "required"}:
                    errors.append(f"{prefix}.llm.mode must be one of: none, optional, required.")
                if mode == "required" and not llm.get("deterministicFallback"):
                    errors.append(f"{prefix}.llm.deterministicFallback must explain behavior for required LLM use.")

            entrypoint = str(capability.get("entrypointPath", "")).strip()
            if entrypoint:
                if Path(entrypoint).is_absolute():
                    errors.append(f"{prefix}.entrypointPath must be relative to the agent directory.")
                elif not (agent_dir / entrypoint).exists():
                    errors.append(f"{prefix}.entrypointPath does not exist: {entrypoint}")

    compatibility = manifest.get("compatibility", {})
    if compatibility and not isinstance(compatibility, dict):
        errors.append("compatibility must be an object when present.")

    errors.extend(find_manifest_secret_values(manifest))

    if errors:
        raise ManifestValidationError(manifest_path, errors)


def load_agent_registry(root: Path) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}

    for manifest_path in agent_manifest_paths(root):
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ManifestValidationError(manifest_path, ["Manifest must be a JSON object."])
        validate_manifest(manifest, manifest_path)

        command_name = str(manifest.get("commandName", "")).strip()
        registry[command_name] = agent_record(manifest, manifest_path)

    return registry


def discover_capabilities(agent_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_capabilities = manifest.get("capabilities")
    if isinstance(manifest_capabilities, list):
        capabilities = []
        for capability in manifest_capabilities:
            if not isinstance(capability, dict):
                continue
            name = str(capability.get("name", "")).strip()
            if not name:
                continue
            capabilities.append(
                {
                    "name": name,
                    "displayName": str(capability.get("displayName", name)).strip(),
                    "description": str(capability.get("description", "")).strip(),
                    "taskTypes": string_list(capability.get("taskTypes", [])),
                    "requiredInputs": capability.get("requiredInputs", []),
                    "configuration": capability.get("configuration", capability.get("config", {})),
                    "compatibility": capability.get("compatibility", {}),
                    "llm": capability.get("llm", {"mode": "none"}),
                    "deterministicFallback": str(capability.get("deterministicFallback", "")).strip(),
                    "entrypointPath": str(capability.get("entrypointPath", "")).strip(),
                }
            )
        return capabilities

    capabilities_root = agent_dir / "capabilities"
    if not capabilities_root.exists():
        return []

    capabilities = []
    for child in sorted(capabilities_root.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        readme = child / "README.md"
        capabilities.append(
            {
                "name": child.name,
                "displayName": child.name,
                "description": first_markdown_paragraph(readme),
                "taskTypes": [],
                "requiredInputs": [],
                "configuration": {},
                "compatibility": {},
                "llm": {"mode": "none"},
                "deterministicFallback": "",
                "entrypointPath": "",
            }
        )
    return capabilities


def first_markdown_paragraph(path: Path) -> str:
    if not path.exists():
        return ""

    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#"):
            return cleaned
    return ""


def agent_record(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    command_name = str(manifest.get("commandName", "")).strip()
    entrypoint_path = str(manifest.get("entrypointPath", "")).strip()
    agent_dir = manifest_path.parent.resolve()
    entrypoint = (agent_dir / entrypoint_path).resolve()
    return {
        "schemaVersion": manifest.get("schemaVersion", SUPPORTED_MANIFEST_SCHEMA_VERSION),
        "id": manifest.get("id", command_name),
        "commandName": command_name,
        "displayName": manifest.get("displayName", command_name),
        "description": manifest.get("description", ""),
        "example": manifest.get("example", "Hello"),
        "version": manifest.get("version", ""),
        "identity": manifest.get("identity", {}),
        "manifest": manifest,
        "entrypoint": str(entrypoint),
        "entrypointPath": entrypoint_path,
        "entrypoints": manifest.get("entrypoints", {}),
        "sourcePath": str(agent_dir),
        "manifestPath": str(manifest_path.resolve()),
        "taskTypes": string_list(manifest.get("taskTypes", [])),
        "requiredInputs": manifest.get("requiredInputs", []),
        "configuration": manifest.get("configuration", {}),
        "compatibility": manifest.get("compatibility", {}),
        "llm": manifest.get("llm", {"mode": "none"}),
        "capabilities": discover_capabilities(agent_dir, manifest),
    }


def load_agent_from_source(source: str) -> dict[str, Any] | None:
    source_path = Path(source).expanduser()
    if not source_path.exists():
        return None

    manifest_path = source_path if source_path.is_file() else source_path / "agent.json"
    if not manifest_path.exists():
        raise ValueError(f"No agent.json manifest found at {source_path}")

    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"Agent manifest must be a JSON object: {manifest_path}")
    validate_manifest(manifest, manifest_path)

    return agent_record(manifest, manifest_path)


def installed_agent_path(command_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", command_name).strip(".-")
    if not safe_name:
        raise ValueError("Agent name cannot be empty.")
    return AGENT_STATE_ROOT / f"{safe_name}.json"


def save_installed_agent(agent: dict[str, Any], launcher_path: Path) -> None:
    ensure_state_layout()
    installed = {
        "commandName": agent["commandName"],
        "schemaVersion": agent.get("schemaVersion", SUPPORTED_MANIFEST_SCHEMA_VERSION),
        "id": agent.get("id", agent["commandName"]),
        "displayName": agent.get("displayName", agent["commandName"]),
        "description": agent.get("description", ""),
        "version": agent.get("version", ""),
        "identity": agent.get("identity", {}),
        "example": agent.get("example", "Hello"),
        "sourcePath": agent.get("sourcePath", ""),
        "manifestPath": agent.get("manifestPath", ""),
        "entrypoint": agent.get("entrypoint", ""),
        "entrypointPath": agent.get("entrypointPath", ""),
        "entrypoints": agent.get("entrypoints", {}),
        "launcherPath": str(launcher_path),
        "installedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "taskTypes": agent.get("taskTypes", []),
        "requiredInputs": agent.get("requiredInputs", []),
        "configuration": agent.get("configuration", {}),
        "compatibility": agent.get("compatibility", {}),
        "llm": agent.get("llm", {"mode": "none"}),
        "manifest": agent.get("manifest", {}),
        "capabilities": agent.get("capabilities", []),
    }
    write_json_atomic(installed_agent_path(agent["commandName"]), installed)


def load_installed_agents() -> dict[str, dict[str, Any]]:
    if not AGENT_STATE_ROOT.exists():
        return {}

    installed: dict[str, dict[str, Any]] = {}
    for path in sorted(AGENT_STATE_ROOT.glob("*.json")):
        record = read_json(path, default={})
        if not isinstance(record, dict):
            continue
        command_name = str(record.get("commandName", "")).strip()
        if command_name:
            installed[command_name] = record
    return installed


def load_installed_agent(command_name: str) -> dict[str, Any] | None:
    record = read_json(installed_agent_path(command_name), default=None)
    return record if isinstance(record, dict) else None


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(value)
    return unique


def required_configuration_names(agent: dict[str, Any], capability: dict[str, Any]) -> list[str]:
    names: list[str] = []
    names.extend(string_list(agent.get("requiredInputs", [])))
    names.extend(string_list(capability.get("requiredInputs", [])))

    for source in (agent.get("configuration", {}), capability.get("configuration", {})):
        if isinstance(source, dict):
            names.extend(string_list(source.get("required", [])))

    return unique_strings(names)


def missing_required_configuration(agent: dict[str, Any], capability: dict[str, Any]) -> list[str]:
    return [name for name in required_configuration_names(agent, capability) if not os.environ.get(name)]


def capability_entrypoint(agent: dict[str, Any], capability: dict[str, Any]) -> Path:
    entrypoint_path = str(capability.get("entrypointPath", "")).strip()
    if not entrypoint_path:
        return Path(str(agent.get("entrypoint", "")))
    return (Path(str(agent.get("sourcePath", ""))) / entrypoint_path).resolve()


def installed_capability_records(installed: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    agents = installed if installed is not None else load_installed_agents()
    records: list[dict[str, Any]] = []
    for command_name, agent in sorted(agents.items()):
        for capability in list_value(agent.get("capabilities", [])):
            if not isinstance(capability, dict):
                continue
            capability_name = str(capability.get("name", "")).strip()
            if not capability_name:
                continue
            task_types = unique_strings(
                string_list(capability.get("taskTypes", [])) + string_list(agent.get("taskTypes", []))
            )
            records.append(
                {
                    "agent": agent,
                    "agentName": command_name,
                    "capability": capability,
                    "capabilityName": capability_name,
                    "displayName": str(capability.get("displayName", capability_name)).strip(),
                    "description": str(capability.get("description", "")).strip(),
                    "taskTypes": task_types,
                    "entrypoint": capability_entrypoint(agent, capability),
                }
            )
    return records


def route_search_text(record: dict[str, Any]) -> str:
    values = [
        record["agentName"],
        record["capabilityName"],
        record.get("displayName", ""),
        record.get("description", ""),
        *record.get("taskTypes", []),
    ]
    return " ".join(str(value).lower() for value in values if value)


def route_score(record: dict[str, Any], query: str) -> int:
    normalized_query = query.lower()
    if not normalized_query.strip():
        return 0

    text = route_search_text(record)
    score = 0
    for task_type in record.get("taskTypes", []):
        normalized_task_type = task_type.lower()
        if normalized_task_type and normalized_task_type in normalized_query:
            score += 5
    for token in re.findall(r"[a-z0-9][a-z0-9_-]*", normalized_query):
        if token and token in text:
            score += 1
    return score


def format_route_candidate(record: dict[str, Any]) -> str:
    task_types = record.get("taskTypes", [])
    suffix = f" [{', '.join(task_types)}]" if task_types else ""
    return f"{record['agentName']}::{record['capabilityName']}{suffix}"


def matching_route_candidates(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str]:
    capabilities = installed_capability_records()
    if args.agent:
        capabilities = [
            record for record in capabilities if record["agentName"].lower() == args.agent.lower()
        ]
    if args.capability:
        capabilities = [
            record
            for record in capabilities
            if record["capabilityName"].lower() == args.capability.lower()
        ]

    query = " ".join(args.request or []).strip()
    if args.task_type:
        requested = args.task_type.lower()
        direct_matches = [
            record
            for record in capabilities
            if requested in {task_type.lower() for task_type in record.get("taskTypes", [])}
        ]
        if not query or len(direct_matches) <= 1:
            return direct_matches, query
        capabilities = direct_matches

    scored = [(route_score(record, query), record) for record in capabilities]
    scored = [(score, record) for score, record in scored if score > 0]
    if not scored:
        return [], query

    best_score = max(score for score, _record in scored)
    return [record for score, record in scored if score == best_score], query


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


def capture(command: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def registry_revision(root: Path) -> str:
    if not root.exists():
        return "missing"
    if not (root / ".git").exists():
        return "not a git checkout"
    revision = capture(["git", "rev-parse", "--short", "HEAD"], root)
    return revision or "unknown"


def registry_status(root: Path) -> str:
    if not root.exists():
        return "missing"
    if not (root / ".git").exists():
        return "not a git checkout"
    status = capture(["git", "status", "--short"], root)
    if status is None:
        return "unknown"
    return "dirty" if status else "clean"


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


def parse_release_version(tag_name: str) -> tuple[int, int, int, tuple[str, ...]] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z0-9_.-]+))?", str(tag_name).strip())
    if not match:
        return None
    prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), prerelease


def compare_release_versions(left: str, right: str) -> int:
    left_version = parse_release_version(left)
    right_version = parse_release_version(right)
    if left_version is None or right_version is None:
        raise ValueError("Release versions must be semver-like.")

    left_core = left_version[:3]
    right_core = right_version[:3]
    if left_core != right_core:
        return 1 if left_core > right_core else -1

    left_prerelease = left_version[3]
    right_prerelease = right_version[3]
    if left_prerelease == right_prerelease:
        return 0
    if not left_prerelease:
        return 1
    if not right_prerelease:
        return -1
    return 1 if left_prerelease > right_prerelease else -1


def release_metadata_url() -> str:
    return os.environ.get("MONGOOSE_RELEASES_API_URL", MONGOOSE_RELEASES_API_URL).strip() or MONGOOSE_RELEASES_API_URL


def deferred_self_update_disabled() -> bool:
    value = os.environ.get("MONGOOSE_DISABLE_DEFERRED_SELF_UPDATE", "")
    return value.strip().lower() in {"1", "true", "yes", "always"}


def fetch_release_metadata(url: str | None = None) -> list[dict[str, Any]]:
    url = url or release_metadata_url()
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Mongoose/{MONGOOSE_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except OSError as exc:
        raise SelfUpdateError(f"Could not reach GitHub Releases: {exc}") from exc

    try:
        releases = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SelfUpdateError("GitHub Releases returned invalid JSON.") from exc
    if not isinstance(releases, list):
        raise SelfUpdateError("GitHub Releases returned an unexpected response.")
    return [release for release in releases if isinstance(release, dict)]


def latest_eligible_release(releases: list[dict[str, Any]], include_prerelease: bool = False) -> dict[str, Any] | None:
    eligible: list[dict[str, Any]] = []
    for release in releases:
        tag_name = str(release.get("tag_name", "")).strip()
        if not tag_name or parse_release_version(tag_name) is None:
            continue
        if release.get("draft"):
            continue
        if release.get("prerelease") and not include_prerelease:
            continue
        eligible.append(release)

    if not eligible:
        return None
    return max(eligible, key=lambda release: parse_release_version(str(release["tag_name"])))


def release_asset(release: dict[str, Any], asset_name: str = MONGOOSE_RELEASE_ASSET_NAME) -> dict[str, Any] | None:
    assets = release.get("assets", [])
    if not isinstance(assets, list):
        return None
    for asset in assets:
        if isinstance(asset, dict) and asset.get("name") == asset_name:
            return asset
    return None


def download_release_asset(asset: dict[str, Any], destination: Path) -> None:
    url = str(asset.get("browser_download_url", "")).strip() or str(asset.get("url", "")).strip()
    if not url:
        raise SelfUpdateError("Release asset did not include a download URL.")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": f"Mongoose/{MONGOOSE_VERSION}",
        },
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with destination.open("wb") as file:
                shutil.copyfileobj(response, file)
    except OSError as exc:
        if destination.exists():
            destination.unlink()
        raise SelfUpdateError(f"Could not download {MONGOOSE_RELEASE_ASSET_NAME}: {exc}") from exc

    if not destination.exists() or destination.stat().st_size == 0:
        raise SelfUpdateError(f"Downloaded {MONGOOSE_RELEASE_ASSET_NAME} was empty.")


def installed_mongoose_exe_path() -> Path:
    return USER_BIN / MONGOOSE_RELEASE_ASSET_NAME


def replace_installed_executable(staged_exe: Path, target_exe: Path) -> str:
    target_exe.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(staged_exe, target_exe)
        return "replaced"
    except OSError as exc:
        if not target_exe.exists():
            raise SelfUpdateError(f"Could not install {target_exe}: {exc}") from exc
        if deferred_self_update_disabled():
            raise SelfUpdateError(
                f"Downloaded update to {staged_exe}, but could not replace {target_exe}: {exc}"
            ) from exc
        try:
            schedule_executable_replacement(staged_exe, target_exe)
        except OSError as schedule_exc:
            raise SelfUpdateError(
                f"Downloaded update to {staged_exe}, but could not replace {target_exe}: {exc}"
            ) from schedule_exc
        return "scheduled"


def schedule_executable_replacement(staged_exe: Path, target_exe: Path) -> Path:
    script_path = APP_ROOT / "apply-mongoose-update.ps1"
    script = """param(
    [Parameter(Mandatory=$true)][int]$ProcessId,
    [Parameter(Mandatory=$true)][string]$StagedExe,
    [Parameter(Mandatory=$true)][string]$TargetExe
)
Wait-Process -Id $ProcessId -ErrorAction SilentlyContinue
Move-Item -LiteralPath $StagedExe -Destination $TargetExe -Force
"""
    atomic_write_text(script_path, script)
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script_path),
            "-ProcessId",
            str(os.getpid()),
            "-StagedExe",
            str(staged_exe),
            "-TargetExe",
            str(target_exe),
        ],
        close_fds=True,
    )
    return script_path


def update_mongoose_cli(include_prerelease: bool = False) -> int:
    print_heading("Mongoose CLI update")
    print(label_line("Installed", version_string()))
    try:
        releases = fetch_release_metadata()
        latest_release = latest_eligible_release(releases, include_prerelease=include_prerelease)
        if latest_release is None:
            print_error("No eligible Mongoose releases were found.")
            return 1

        latest_tag = str(latest_release["tag_name"])
        latest_version = latest_tag[1:] if latest_tag.startswith("v") else latest_tag
        print(label_line("Latest", latest_tag))
        if compare_release_versions(MONGOOSE_VERSION, latest_version) >= 0:
            print_success(f"Mongoose is already current: {MONGOOSE_VERSION}")
            return 0

        asset = release_asset(latest_release)
        if asset is None:
            print_error(f"Release {latest_tag} does not include {MONGOOSE_RELEASE_ASSET_NAME}.")
            return 1

        target_exe = installed_mongoose_exe_path()
        staged_exe = APP_ROOT / f".{MONGOOSE_RELEASE_ASSET_NAME}.{latest_tag}.{os.getpid()}.download"
        print(label_line("Download", str(asset.get("browser_download_url", asset.get("url", ""))), "muted"))
        download_release_asset(asset, staged_exe)
        result = replace_installed_executable(staged_exe, target_exe)
    except (SelfUpdateError, ValueError) as exc:
        print_error(str(exc))
        print_muted("Retry later, or download mongoose.exe manually from the GitHub Release.")
        return 1

    if result == "scheduled":
        print_success(f"Downloaded Mongoose {latest_version}; replacement will finish after this command exits.")
    else:
        print_success(f"Updated Mongoose to {latest_version}: {target_exe}")
    print_muted("Run `mongoose --version` in a new terminal to confirm the installed release.")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    ensure_state_layout()
    registry_root = Path(args.registry_root).expanduser().resolve()
    config = {
        "registryUrl": args.registry_url,
        "registryPath": str(registry_root),
    }
    save_config(config)
    USER_BIN.mkdir(parents=True, exist_ok=True)

    print_success("Mongoose configured.")
    print(label_line("Registry", registry_root))
    print(label_line("Config", CONFIG_PATH))
    print("")
    print_heading("Try")
    print("mongoose list")
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    paths = ensure_state_layout() if args.init else state_contract()
    if args.cleanup_logs:
        removed = cleanup_logs(args.log_retention_days)
        print_success(f"Removed {len(removed)} expired log file(s).")
        print("")

    if args.json:
        print(json.dumps(paths, indent=2, sort_keys=True))
        return 0

    print_heading("Mongoose local state")
    for name, path in paths.items():
        if name in {"version", "registryStatus"}:
            print(f"  {label_line(name, path, 'success' if path == 'clean' else 'selected')}")
        else:
            print(f"  {label_line(name, path, 'muted')}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    installed = load_installed_agents()
    if args.installed:
        if not installed:
            print_warning("No installed agents found.")
            return 0

        print_heading("Installed agents")
        for command_name, agent in sorted(installed.items()):
            version = f" v{agent.get('version')}" if agent.get("version") else ""
            description = agent.get("description")
            line = f"  {command_name}{version}"
            if description:
                line = f"{line} - {description}"
            print(line)
        return 0

    config = load_config()
    root = ensure_registry(config)
    agents = load_agent_registry(root)

    if not agents and not installed:
        print_warning("No installable agents found.")
        return 0

    if agents:
        print_heading("Available agents")
        for command_name, agent in sorted(agents.items()):
            description = agent.get("description")
            installed_marker = " [installed]" if command_name in installed else ""
            if description:
                print(f"  {command_name}{installed_marker} - {description}")
            else:
                print(f"  {command_name}{installed_marker}")

    if installed:
        print("")
        print_heading("Installed agents")
        for command_name, agent in sorted(installed.items()):
            print(f"  {command_name} - {agent.get('sourcePath', '')}")

    return 0


def cmd_capabilities(_: argparse.Namespace) -> int:
    capabilities = installed_capability_records()
    if not capabilities:
        print_warning("No installed capabilities found.")
        print_muted("Install an agent first: mongoose install <agent>")
        return 0

    print_heading("Installed capabilities")
    for record in capabilities:
        line = f"  {format_route_candidate(record)}"
        description = record.get("description")
        if description:
            line = f"{line} - {description}"
        print(line)
        required = required_configuration_names(record["agent"], record["capability"])
        if required:
            print(f"    required config: {', '.join(required)}")
        llm = record["capability"].get("llm", {})
        if isinstance(llm, dict) and llm.get("mode", "none") != "none":
            print(f"    llm: {llm.get('mode')}")
    return 0


def create_agent_launcher(command_name: str, entrypoint: str) -> Path:
    USER_BIN.mkdir(parents=True, exist_ok=True)
    launcher_path = USER_BIN / f"{command_name}.cmd"
    launcher = f'@echo off\npython "{entrypoint}" ask %*\n'
    launcher_path.write_text(launcher, encoding="ascii")
    return launcher_path


def cmd_install(args: argparse.Namespace) -> int:
    source_agent = load_agent_from_source(args.agent)
    if source_agent is not None:
        agent = source_agent
        agents: dict[str, dict[str, Any]] = {}
    else:
        config = load_config()
        root = ensure_registry(config)
        agents = load_agent_registry(root)
        agent = agents.get(args.agent)

    if agent is None:
        print_error(f"Agent '{args.agent}' does not exist.")
        print("")
        print_heading("Available agents")
        for command_name in sorted(agents):
            print(f"  {command_name}")
        return 1

    launcher_path = create_agent_launcher(agent["commandName"], agent["entrypoint"])
    save_installed_agent(agent, launcher_path)
    print_success(f"Installed {agent['displayName']} as {agent['commandName']}.")
    print(label_line("Launcher", launcher_path, "muted"))
    print(label_line("State", installed_agent_path(agent["commandName"]), "muted"))
    print("")
    print_heading("Try")
    print(f"{agent['commandName']} \"{agent.get('example', 'Hello')}\"")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    launcher_path = USER_BIN / f"{args.agent}.cmd"
    state_path = installed_agent_path(args.agent)
    removed = False
    if not launcher_path.exists():
        print_warning(f"Agent command '{args.agent}' is not installed.")
    else:
        launcher_path.unlink()
        print_success(f"Removed {launcher_path}")
        removed = True

    if state_path.exists():
        state_path.unlink()
        print_success(f"Removed {state_path}")
        removed = True

    if not removed:
        print_warning(f"No installed state found for '{args.agent}'.")
    return 0


def print_agent_details(agent: dict[str, Any], installed: bool) -> None:
    print_heading(f"Agent: {agent.get('commandName', '')}")
    print(label_line("ID", agent.get("id", agent.get("commandName", ""))))
    print(label_line("Display name", agent.get("displayName", "")))
    print(label_line("Manifest schema", agent.get("schemaVersion", SUPPORTED_MANIFEST_SCHEMA_VERSION)))
    if agent.get("version"):
        print(label_line("Version", agent["version"]))
    print(label_line("Status", "installed" if installed else "available", "success" if installed else "warning"))
    if agent.get("description"):
        print(label_line("Description", agent["description"]))
    print(label_line("Source", agent.get("sourcePath", ""), "muted"))
    print(label_line("Manifest", agent.get("manifestPath", ""), "muted"))
    print(label_line("Entrypoint", agent.get("entrypoint", ""), "muted"))
    if agent.get("launcherPath"):
        print(label_line("Launcher", agent["launcherPath"], "muted"))
    if agent.get("taskTypes"):
        print(f"Task types: {', '.join(str(item) for item in agent['taskTypes'])}")
    if agent.get("requiredInputs"):
        print(f"Required inputs: {', '.join(str(item) for item in agent['requiredInputs'])}")
    configuration = agent.get("configuration", {})
    if isinstance(configuration, dict) and configuration:
        required_config = string_list(configuration.get("required", []))
        optional_config = string_list(configuration.get("optional", []))
        if required_config:
            print(f"Required config: {', '.join(required_config)}")
        if optional_config:
            print(f"Optional config: {', '.join(optional_config)}")
    llm = agent.get("llm", {})
    if isinstance(llm, dict):
        print(f"LLM mode: {llm.get('mode', 'none')}")
    capabilities = agent.get("capabilities", [])
    print("")
    print_heading("Capabilities")
    if not capabilities:
        print("  none declared")
        return
    for capability in capabilities:
        name = capability.get("name", "")
        description = capability.get("description", "")
        task_types = capability.get("taskTypes", [])
        required_inputs = capability.get("requiredInputs", [])
        configuration = capability.get("configuration", {})
        llm = capability.get("llm", {})
        line = f"  {name}"
        if description:
            line = f"{line} - {description}"
        if task_types:
            line = f"{line} [{', '.join(str(item) for item in task_types)}]"
        print(line)
        if required_inputs:
            print(f"    inputs: {', '.join(str(item) for item in required_inputs)}")
        if isinstance(configuration, dict) and configuration.get("required"):
            print(f"    required config: {', '.join(string_list(configuration.get('required')))}")
        if isinstance(llm, dict) and llm.get("mode", "none") != "none":
            print(f"    llm: {llm.get('mode')}")


def cmd_show(args: argparse.Namespace) -> int:
    installed = load_installed_agent(args.agent)
    if installed is not None:
        print_agent_details(installed, installed=True)
        return 0

    config = load_config()
    root = ensure_registry(config)
    available = load_agent_registry(root).get(args.agent)
    if available is not None:
        print_agent_details(available, installed=False)
        return 0

    print_error(f"Agent '{args.agent}' was not found.")
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    agent = load_installed_agent(args.agent)
    if agent is None:
        print_error(f"Agent '{args.agent}' is not installed. Run: mongoose install {args.agent}")
        return 1

    entrypoint = Path(str(agent.get("entrypoint", "")))
    if not entrypoint.exists():
        print_error(f"Installed agent entrypoint no longer exists: {entrypoint}")
        return 1

    agent_args = args.agent_args or ["ask", str(agent.get("example", "Hello"))]
    completed = subprocess.run(
        [sys.executable, str(entrypoint), *agent_args],
        check=False,
    )
    return completed.returncode


def cmd_route(args: argparse.Namespace) -> int:
    installed = load_installed_agents()
    if not installed:
        print_error("No installed agents found.")
        print_muted("Install an agent first: mongoose install <agent>")
        return 1

    all_capabilities = installed_capability_records(installed)
    if not all_capabilities:
        print_error("No installed capabilities found.")
        print_muted("Install agents with manifest capability metadata before routing.")
        return 1

    matches, query = matching_route_candidates(args)
    if not matches:
        print_error("No installed capability can handle that request.")
        if args.task_type:
            print(f"Requested task type: {args.task_type}")
        elif query:
            print(f"Request: {query}")
        print("")
        print_heading("Installed capabilities")
        for record in all_capabilities:
            print(f"  {format_route_candidate(record)}")
        return 1

    if len(matches) > 1:
        print_warning("Ambiguous request. More than one installed capability matched:")
        for record in matches:
            print(f"  {format_route_candidate(record)}")
        print("")
        print_muted("Refine with --agent, --capability, or a more specific --task-type.")
        return 1

    selected = matches[0]
    missing = missing_required_configuration(selected["agent"], selected["capability"])
    if missing:
        print_warning(f"Selected {format_route_candidate(selected)}, but required configuration is missing:")
        for name in missing:
            print(f"  {name}")
        print("")
        print_muted("Set the missing environment variables or choose another capability.")
        return 1

    llm = selected["capability"].get("llm", {})
    if isinstance(llm, dict) and llm.get("mode") == "required":
        print_warning(f"Selected {format_route_candidate(selected)}, but it requires an LLM runtime.")
        print_muted("Mongoose LLM runtime configuration is not available yet.")
        return 1

    entrypoint = Path(str(selected["entrypoint"]))
    if not entrypoint.exists():
        print_error(f"Selected {format_route_candidate(selected)}, but its entrypoint does not exist: {entrypoint}")
        return 1

    agent_args = [selected["capabilityName"], *(args.request or [])]
    print(label_line("Selected", format_route_candidate(selected), "success"))
    if args.dry_run:
        print(label_line("Entrypoint", entrypoint, "muted"))
        print(label_line("Arguments", " ".join(agent_args), "muted"))
        return 0

    completed = subprocess.run(
        [sys.executable, str(entrypoint), *agent_args],
        check=False,
    )
    return completed.returncode


def cmd_update(args: argparse.Namespace) -> int:
    if args.self_update:
        return update_mongoose_cli(include_prerelease=args.include_prerelease)

    print_heading("Mongoose registry update")
    config = load_config()
    root = registry_path(config)
    registry_url = config.get("registryUrl", DEFAULT_REGISTRY_URL)

    if root.exists() and (root / ".git").exists():
        run(["git", "pull", "--ff-only"], cwd=root)
        print_success(f"Updated registry at {root}")
        return 0

    if root.exists():
        print_error(f"Registry path exists but is not a Git repository: {root}")
        return 1

    root.parent.mkdir(parents=True, exist_ok=True)
    local_source = local_registry_source(registry_url)
    if local_source is not None:
        shutil.copytree(
            local_source,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        print_success(f"Copied local registry to {root}")
        return 0

    run(["git", "clone", registry_url, str(root)])
    print_success(f"Cloned registry to {root}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.path:
        root = Path(args.path).expanduser().resolve()
    else:
        config = load_config()
        root = ensure_registry(config)

    manifest_path = root if root.is_file() else root / "agent.json"
    if manifest_path.exists() and manifest_path.is_file():
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ManifestValidationError(manifest_path, ["Manifest must be a JSON object."])
        validate_manifest(manifest, manifest_path)
        print_success(f"Manifest valid: {manifest_path}")
        return 0

    manifests = agent_manifest_paths(root)
    if not manifests:
        print_error(f"No agent manifests found under {root}")
        return 1

    for path in manifests:
        manifest = read_json(path)
        if not isinstance(manifest, dict):
            raise ManifestValidationError(path, ["Manifest must be a JSON object."])
        validate_manifest(manifest, path)
        print_success(f"Manifest valid: {path}")
    print_success(f"Validated {len(manifests)} manifest(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    examples = """examples:
  mongoose --version
  mongoose list
  mongoose list --installed
  mongoose capabilities
  mongoose install Njord
  mongoose install C:\\path\\to\\agent
  mongoose show Njord
  mongoose run Njord config status
  mongoose route --task-type budget-summary "current budget"
  mongoose validate
  mongoose remove Njord
  mongoose update
  mongoose update --self
  mongoose state --init
  mongoose setup --registry-root C:\\path\\to\\Agents

workflow:
  1. Run `mongoose list` to see available agents.
  2. Run `mongoose install <agent-or-path>` to install one as a command.
  3. Run `mongoose show <agent>` to inspect installed metadata and capabilities.
  4. Run `mongoose capabilities` to inspect routeable installed capabilities.
  5. Run `mongoose route --task-type <type> ...` or `mongoose run <agent> ...`.
  6. Run `mongoose update` to pull registry changes from GitHub.
  7. Run `mongoose update --self` to update the installed Mongoose CLI.
"""
    parser = argparse.ArgumentParser(
        prog="mongoose",
        description="Install, inspect, run, remove, and update local agents.",
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version_string(),
        help="Print the Mongoose CLI version.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color in human-readable output.",
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
        help="List available or installed agents.",
        description="List installable agents discovered from agents/*/agent.json and installed local state.",
    )
    list_parser.add_argument(
        "--installed",
        action="store_true",
        help="Only list agents installed into local Mongoose state.",
    )
    list_parser.set_defaults(handler=cmd_list)

    capabilities = subparsers.add_parser(
        "capabilities",
        aliases=["caps"],
        help="List installed routeable capabilities.",
        description="List capability metadata from installed agent manifests for Mongoose routing.",
    )
    capabilities.set_defaults(handler=cmd_capabilities)

    install = subparsers.add_parser(
        "install",
        help="Install an agent as a user-local command.",
        description="Install an agent command into the user-local Agents bin directory from a registry name or local agent path.",
    )
    install.add_argument("agent", help="Agent commandName or local agent path to install, such as Njord.")
    install.set_defaults(handler=cmd_install)

    uninstall = subparsers.add_parser(
        "uninstall",
        aliases=["remove", "rm"],
        help="Uninstall a user-local agent command.",
        description="Remove an installed agent command and local Mongoose install state.",
    )
    uninstall.add_argument("agent", help="Agent commandName to remove, such as Njord.")
    uninstall.set_defaults(handler=cmd_uninstall)

    show = subparsers.add_parser(
        "show",
        help="Show installed agent metadata and capabilities.",
        description="Show manifest, entrypoint, source, launcher, and capability metadata for an agent.",
    )
    show.add_argument("agent", help="Agent commandName to inspect, such as Njord.")
    show.set_defaults(handler=cmd_show)

    run_parser = subparsers.add_parser(
        "run",
        help="Run an installed agent entrypoint.",
        description="Dispatch arguments to an installed agent entrypoint through Mongoose.",
    )
    run_parser.add_argument("agent", help="Installed agent commandName to run, such as Njord.")
    run_parser.add_argument(
        "agent_args",
        nargs=argparse.REMAINDER,
        help="Arguments to pass to the agent entrypoint.",
    )
    run_parser.set_defaults(handler=cmd_run)

    route = subparsers.add_parser(
        "route",
        help="Route a request to an installed agent capability.",
        description="Select an installed agent capability by task type or request text, then dispatch to it.",
    )
    route.add_argument(
        "--task-type",
        help="Direct task classification hint, such as budget-summary or finance.",
    )
    route.add_argument("--agent", help="Restrict routing to one installed agent commandName.")
    route.add_argument("--capability", help="Restrict routing to one capability name.")
    route.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the selected capability and invocation without running it.",
    )
    route.add_argument(
        "request",
        nargs=argparse.REMAINDER,
        help="Request words to pass to the selected capability.",
    )
    route.set_defaults(handler=cmd_route)

    validate = subparsers.add_parser(
        "validate",
        help="Validate agent manifest metadata.",
        description="Validate one agent manifest, one agent directory, or all manifests in the configured registry.",
    )
    validate.add_argument(
        "path",
        nargs="?",
        help="Optional manifest, agent directory, or registry root path to validate.",
    )
    validate.set_defaults(handler=cmd_validate)

    update = subparsers.add_parser(
        "update",
        help="Pull registry updates, or update the installed Mongoose CLI with --self.",
        description=(
            "Update the configured Git-backed registry with git pull --ff-only, or clone it if missing. "
            "Use --self to update the installed Mongoose CLI from GitHub Releases."
        ),
    )
    update.add_argument(
        "--self",
        action="store_true",
        dest="self_update",
        help="Update the installed Mongoose CLI from the latest stable GitHub Release.",
    )
    update.add_argument(
        "--include-prerelease",
        action="store_true",
        help="Allow prerelease GitHub Releases when used with --self.",
    )
    update.set_defaults(handler=cmd_update)

    return parser


def version_string() -> str:
    if MONGOOSE_RELEASE_KIND == "official":
        tag_suffix = f", {MONGOOSE_RELEASE_TAG}" if MONGOOSE_RELEASE_TAG else ""
        return f"mongoose {MONGOOSE_VERSION} (official release{tag_suffix})"
    return f"mongoose {MONGOOSE_VERSION} (development)"


def main() -> int:
    configure_output()
    parser = build_parser()
    args = parser.parse_args()
    set_output_color(should_use_color(getattr(args, "no_color", False)))
    try:
        return args.handler(args)
    except ValueError as exc:
        print_error(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

