"""Command runner for the Midas agent."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


AGENT_ROOT = Path(__file__).resolve().parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from router import route_request


def configure_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_module(module_name: str, module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_hello_world(name: str) -> str:
    module_path = AGENT_ROOT / "capabilities" / "hello-world" / "hello_world.py"
    module = load_module("midas_hello_world", module_path)
    return module.run(name)


def run_hello_world_with_status(name: str) -> tuple[bool, str]:
    module_path = AGENT_ROOT / "capabilities" / "hello-world" / "hello_world.py"
    module = load_module("midas_hello_world", module_path)
    return module.run_with_status(name)


def run_ynab_budget_summary() -> tuple[bool, str]:
    module_path = (
        AGENT_ROOT
        / "capabilities"
        / "ynab-budget-summary"
        / "ynab_budget_summary.py"
    )
    module = load_module("midas_ynab_budget_summary", module_path)
    return module.load_latest_summary()


def answer_request(request: str) -> tuple[bool, str]:
    route = route_request(request)

    if route.capability == "hello-world":
        ok, output = run_hello_world_with_status("Midas")
    elif route.capability == "ynab-budget-summary":
        ok, output = run_ynab_budget_summary()
    else:
        return False, f"I do not know how to run capability: {route.capability}"

    return ok, f"Request: {request}\nCapability: {route.capability}\nReason: {route.reason}\n\n{output}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Midas agent capabilities."
    )
    subparsers = parser.add_subparsers(
        dest="capability",
        required=True,
        help="Capability to run.",
    )

    hello_world = subparsers.add_parser(
        "hello-world",
        help="Run the hello world capability.",
    )
    hello_world.add_argument(
        "--name",
        default="there",
        help="Optional name or context to include in the greeting.",
    )

    subparsers.add_parser(
        "ynab-budget-summary",
        help="Summarize the latest available YNAB budget state.",
    )

    ask = subparsers.add_parser(
        "ask",
        help="Route a natural-language request to the right capability.",
    )
    ask.add_argument(
        "request",
        nargs=argparse.REMAINDER,
        help="Natural-language request for the Midas agent.",
    )

    return parser


def main() -> None:
    configure_output()
    parser = build_parser()
    args = parser.parse_args()

    if args.capability == "hello-world":
        ok, output = run_hello_world_with_status(args.name)
        print(output)
        if not ok:
            sys.exit(1)
        return

    if args.capability == "ynab-budget-summary":
        ok, output = run_ynab_budget_summary()
        print(output)
        if not ok:
            sys.exit(1)
        return

    if args.capability == "ask":
        request = " ".join(args.request).strip()
        if not request:
            parser.error("ask requires a natural-language request.")

        ok, output = answer_request(request)
        print(output)
        if not ok:
            sys.exit(1)
        return

    parser.error(f"Unknown capability: {args.capability}")


if __name__ == "__main__":
    main()
