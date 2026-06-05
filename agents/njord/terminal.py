"""Terminal formatting helpers for Njord command output."""

from __future__ import annotations

import os
import sys


ANSI_RESET = "\033[0m"
ANSI_STYLES = {
    "heading": "\033[36;1m",
    "success": "\033[32;1m",
    "warning": "\033[33;1m",
    "error": "\033[31;1m",
    "muted": "\033[2m",
    "selected": "\033[34;1m",
}
SECTION_HEADINGS = {
    "Boundaries",
    "Capabilities",
    "Connection status",
    "Njord budget summary",
    "Njord configuration status",
    "Njord spending review",
    "Njord weekly financial brief",
    "Notable transactions",
    "Observations",
    "Previous period comparison",
    "Recommended reviews/actions",
    "Review items",
    "Review needed",
    "Snapshot",
    "Spending highlights",
    "Suggested next actions",
    "Top spending categories",
    "Totals",
    "Validation",
}


def color_requested_by_env() -> bool:
    value = os.environ.get("NJORD_FORCE_COLOR") or os.environ.get("MONGOOSE_FORCE_COLOR", "")
    return value.strip().lower() in {"1", "true", "yes", "always"}


def color_disabled_by_env() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("NJORD_NO_COLOR") or os.environ.get("MONGOOSE_NO_COLOR"):
        return True
    color_mode = (os.environ.get("NJORD_COLOR") or os.environ.get("MONGOOSE_COLOR", "")).strip().lower()
    return color_mode in {"0", "false", "never", "no"}


def should_use_color(no_color: bool = False) -> bool:
    if no_color or color_disabled_by_env():
        return False
    return color_requested_by_env() or sys.stdout.isatty()


def styled(text: str, style: str, enabled: bool) -> str:
    if not enabled:
        return text
    prefix = ANSI_STYLES.get(style)
    if not prefix:
        return text
    return f"{prefix}{text}{ANSI_RESET}"


def style_output(text: str, enabled: bool) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            lines.append(line)
        elif stripped in SECTION_HEADINGS:
            lines.append(styled(line, "heading", enabled))
        elif lower.startswith(("error", "ynab_access_token is not configured", "ynab_budget_id is not configured")):
            lines.append(styled(line, "error", enabled))
        elif "failed" in lower or "missing" in lower or "could not" in lower:
            lines.append(styled(line, "warning", enabled))
        elif lower.startswith(("plan:", "period:", "snapshot freshness:", "request:", "capability:", "reason:")):
            label, _, value = line.partition(":")
            lines.append(f"{styled(label + ':', 'selected', enabled)}{value}")
        elif stripped.startswith("- ["):
            style = "warning" if any(word in lower for word in ("high", "medium", "risk", "review")) else "success"
            lines.append(styled(line, style, enabled))
        elif stripped.startswith("- "):
            lines.append(styled(line, "muted", enabled))
        else:
            lines.append(line)
    return "\n".join(lines)
