"""Validate release version consistency for Mongoose."""

from __future__ import annotations

import os
import re
from pathlib import Path


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


REPO_ROOT = Path(__file__).resolve().parents[1]
MONGOOSE_CLI = REPO_ROOT / "mongoose" / "mongoose.py"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
EMBEDDER = REPO_ROOT / "mongoose" / "launcher" / "embed_mongoose.py"


def read_mongoose_version() -> str:
    source = MONGOOSE_CLI.read_text(encoding="utf-8")
    match = re.search(r'^MONGOOSE_VERSION\s*=\s*"([^"]+)"', source, re.MULTILINE)
    assert_true(match is not None, "MONGOOSE_VERSION was not found in mongoose.py.")
    return match.group(1)


def read_constant(name: str) -> str:
    source = MONGOOSE_CLI.read_text(encoding="utf-8")
    match = re.search(rf'^{name}\s*=\s*"([^"]*)"', source, re.MULTILINE)
    assert_true(match is not None, f"{name} was not found in mongoose.py.")
    return match.group(1)


version = read_mongoose_version()
assert_true(
    re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9_.-]+)?", version),
    "MONGOOSE_VERSION is not semver-like.",
)

changelog = CHANGELOG.read_text(encoding="utf-8")
assert_true(f"## v{version}" in changelog, f"CHANGELOG.md is missing a v{version} section.")
assert_true(read_constant("MONGOOSE_RELEASE_KIND") == "development", "Source Mongoose release kind must default to development.")
assert_true(read_constant("MONGOOSE_RELEASE_TAG") == "", "Source Mongoose release tag must default to empty.")
assert_true("GITHUB_REF_TYPE" in EMBEDDER.read_text(encoding="utf-8"), "Embedder must derive official release metadata from tag builds.")

github_ref_type = os.environ.get("GITHUB_REF_TYPE", "")
github_ref_name = os.environ.get("GITHUB_REF_NAME", "")
if github_ref_type == "tag" or github_ref_name.startswith("v"):
    expected_tag = f"v{version}"
    assert_true(
        github_ref_name == expected_tag,
        f"Release tag {github_ref_name!r} does not match Mongoose CLI version {expected_tag!r}.",
    )

print(f"Release version validation passed for mongoose {version}.")
