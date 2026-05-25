"""Hello world capability for the Midas agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


YNAB_API_BASE_URL = "https://api.ynab.com/v1"


@dataclass(frozen=True)
class YnabConnectionResult:
    ok: bool
    message: str


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        cleaned_line = line.strip()
        if not cleaned_line or cleaned_line.startswith("#") or "=" not in cleaned_line:
            continue

        key, value = cleaned_line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def ynab_access_token() -> str:
    load_dotenv(repo_root() / ".env")
    return os.environ.get("YNAB_ACCESS_TOKEN", "").strip()


def test_ynab_connection() -> YnabConnectionResult:
    token = ynab_access_token()
    if not token:
        return YnabConnectionResult(
            ok=False,
            message=(
                "YNAB connection was not tested because YNAB_ACCESS_TOKEN is not set. "
                "Add it to the repository root .env file."
            ),
        )

    request = urllib.request.Request(
        f"{YNAB_API_BASE_URL}/plans",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            return YnabConnectionResult(
                ok=False,
                message=(
                    "YNAB connection failed: the access token was rejected. "
                    "Check YNAB_ACCESS_TOKEN in .env."
                ),
            )

        return YnabConnectionResult(
            ok=False,
            message=f"YNAB connection failed with HTTP {error.code}.",
        )
    except urllib.error.URLError as error:
        return YnabConnectionResult(
            ok=False,
            message=f"YNAB connection failed: {error.reason}.",
        )
    except TimeoutError:
        return YnabConnectionResult(
            ok=False,
            message="YNAB connection failed: request timed out.",
        )
    except json.JSONDecodeError:
        return YnabConnectionResult(
            ok=False,
            message="YNAB connection failed: response was not valid JSON.",
        )

    plans = payload.get("data", {}).get("plans", [])
    plan_count = len(plans)
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
