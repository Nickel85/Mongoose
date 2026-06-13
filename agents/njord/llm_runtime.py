"""Mongoose-managed LLM narration helpers for Njord."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_CONTEXT_CHARS = 5000


@dataclass(frozen=True)
class LlmNarration:
    ok: bool
    text: str = ""
    profile: str = ""
    diagnostic: str = ""


def _runtime_context() -> dict:
    context_path = os.environ.get("MONGOOSE_RUNTIME_CONTEXT", "").strip()
    if not context_path:
        return {}
    path = Path(context_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _invoke_command_from_context() -> list[str]:
    context = _runtime_context()
    llm = context.get("providers", {}).get("llm", {}) if isinstance(context.get("providers", {}), dict) else {}
    command = llm.get("invokeCommand", []) if isinstance(llm, dict) else []
    if isinstance(command, list) and all(isinstance(item, str) and item for item in command):
        return command
    return []


def _fallback_invoke_command() -> list[str]:
    explicit = os.environ.get("MONGOOSE_LLM_INVOKE", "").strip()
    if explicit:
        return shlex.split(explicit)
    return []


def llm_invoke_command() -> list[str]:
    return _invoke_command_from_context() or _fallback_invoke_command()


def redact_for_prompt(text: str) -> str:
    redacted_lines: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in ("access token", "api key", "authorization", "secret", "password")):
            redacted_lines.append("[redacted secret-bearing line]")
        else:
            redacted_lines.append(line)
    return "\n".join(redacted_lines)[:MAX_CONTEXT_CHARS]


def build_narration_prompt(*, request: str, capability: str, deterministic_output: str) -> str:
    context = redact_for_prompt(deterministic_output)
    return "\n".join(
        [
            "You are Njord, a read-only budgeting assistant.",
            "Explain the deterministic finance facts below in concise, practical language.",
            "Do not invent balances, transactions, or budget changes.",
            "Do not recommend or claim that any YNAB write has happened.",
            "",
            f"User request: {request}",
            f"Deterministic capability: {capability}",
            "",
            "Deterministic output:",
            context,
        ]
    )


def narrate_finance_response(*, request: str, capability: str, deterministic_output: str) -> LlmNarration:
    command = llm_invoke_command()
    if not command:
        return LlmNarration(False, diagnostic="No Mongoose LLM invocation command is available.")

    prompt = build_narration_prompt(
        request=request,
        capability=capability,
        deterministic_output=deterministic_output,
    )
    system_prompt = (
        "You narrate read-only finance analysis from deterministic facts. "
        "Keep generated text separate from facts and never propose unapproved writes."
    )
    completed = subprocess.run(
        [*command, "--system", system_prompt],
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
        timeout=45,
    )
    output = completed.stdout.strip()
    if not output:
        diagnostic = completed.stderr.strip() or "Mongoose LLM invocation returned no output."
        return LlmNarration(False, diagnostic=diagnostic)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return LlmNarration(False, diagnostic="Mongoose LLM invocation returned invalid JSON.")

    if not isinstance(payload, dict) or not payload.get("ok"):
        message = str(payload.get("message", "") if isinstance(payload, dict) else "").strip()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        if isinstance(error, dict) and error.get("message"):
            message = str(error.get("message"))
        return LlmNarration(False, diagnostic=message or "Mongoose LLM invocation failed.")

    response = payload.get("response", {}) if isinstance(payload.get("response", {}), dict) else {}
    text = str(response.get("content", "")).strip()
    if not text:
        return LlmNarration(False, diagnostic="Mongoose LLM invocation returned an empty response.")
    return LlmNarration(True, text=text, profile=str(payload.get("profile", "")))
