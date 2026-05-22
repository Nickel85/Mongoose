"""Command runner for the Personal CFO agent."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


AGENT_ROOT = Path(__file__).resolve().parent


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
    module = load_module("personal_cfo_hello_world", module_path)
    return module.run(name)


def run_hello_world_with_status(name: str) -> tuple[bool, str]:
    module_path = AGENT_ROOT / "capabilities" / "hello-world" / "hello_world.py"
    module = load_module("personal_cfo_hello_world", module_path)
    return module.run_with_status(name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Personal CFO agent capabilities."
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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.capability == "hello-world":
        ok, output = run_hello_world_with_status(args.name)
        print(output)
        if not ok:
            sys.exit(1)
        return

    parser.error(f"Unknown capability: {args.capability}")


if __name__ == "__main__":
    main()
