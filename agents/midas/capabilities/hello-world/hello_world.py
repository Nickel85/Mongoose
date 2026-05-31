"""Hello world capability for the Midas agent."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


AGENT_ROOT = Path(__file__).resolve().parents[2]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from ynab_api import list_plans


@dataclass(frozen=True)
class YnabConnectionResult:
    ok: bool
    message: str


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_ynab_connection() -> YnabConnectionResult:
    result = list_plans()
    if not result.ok:
        return YnabConnectionResult(
            ok=False,
            message=f"YNAB connection failed: {result.message}",
        )

    plan_count = len(result.items)
    return YnabConnectionResult(
        ok=True,
        message=f"YNAB connection succeeded. Found {plan_count} plan(s).",
    )


def build_greeting(name: str, connection_result: YnabConnectionResult) -> str:
    """Build the greeting returned by this capability."""
    cleaned_name = name.strip() or "there"
    return (
        f"Hello, {cleaned_name}.\n"
        "Midas is ready to review your financial life.\n"
        f"{connection_result.message}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Midas hello world capability."
    )
    parser.add_argument(
        "--name",
        default="there",
        help="Optional name or context to include in the greeting.",
    )
    return parser.parse_args()


def run(name: str = "there") -> str:
    """Run the capability and return its output."""
    _, output = run_with_status(name)
    return output


def run_with_status(name: str = "there") -> tuple[bool, str]:
    """Run the capability and return success status with its output."""
    connection_result = test_ynab_connection()
    return connection_result.ok, build_greeting(name, connection_result)


def main() -> None:
    configure_output()
    args = parse_args()
    ok, output = run_with_status(args.name)
    print(output)

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
