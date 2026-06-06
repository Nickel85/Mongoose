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
MONGOOSE_BUILD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "mongoose-build.yml"
INSTALL_VALIDATION_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "install-validation.yml"
MONGOOSE_SMOKE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "mongoose-smoke.yml"
TEXT_EXTENSIONS = {
    ".cmd",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
}
IGNORED_PARTS = (
    ".git",
    ".test-localappdata-exe",
    ".test-localappdata-mongoose",
    ".test-localappdata-mongoose-exe",
    ".test-localappdata-mongoose-installed-self-update",
    ".test-localappdata-mongoose-self-update",
    ".test-localappdata-mongoose-state",
    ".test-mongoose-fixtures",
    ".test-mongoose-self-update-fixtures",
    ".test-mongoose-update-registry",
    "__pycache__",
    "dist",
    "mongoose_py.inc",
)
LEGACY_REPO_REFERENCE = "Nickel85/" + "Agents"
LEGACY_REGISTRY_URL = "https://github.com/Nickel85/" + "Agents.git"


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


def active_text_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            files.append(path)
    return sorted(files)


def assert_workflow_runs_release_validation(path: Path) -> str:
    workflow = path.read_text(encoding="utf-8")
    assert_true(
        "python ./tests/release-version-validation.py" in workflow,
        f"{path.relative_to(REPO_ROOT)} does not run release-version-validation.py.",
    )
    return workflow


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
assert_true(
    read_constant("DEFAULT_REGISTRY_URL") == "https://github.com/Nickel85/Mongoose.git",
    "DEFAULT_REGISTRY_URL must point at the public Mongoose repository.",
)

for path in active_text_files():
    text = path.read_text(encoding="utf-8")
    assert_true(
        LEGACY_REPO_REFERENCE not in text,
        f"{path.relative_to(REPO_ROOT)} contains a stale legacy repository reference.",
    )
    assert_true(
        LEGACY_REGISTRY_URL not in text,
        f"{path.relative_to(REPO_ROOT)} contains the stale legacy registry URL.",
    )

build_workflow = assert_workflow_runs_release_validation(MONGOOSE_BUILD_WORKFLOW)
install_workflow = assert_workflow_runs_release_validation(INSTALL_VALIDATION_WORKFLOW)
smoke_workflow = assert_workflow_runs_release_validation(MONGOOSE_SMOKE_WORKFLOW)
validation_index = build_workflow.index("python ./tests/release-version-validation.py")
build_index = build_workflow.index("run: build-mongoose.cmd")
upload_index = build_workflow.index("uses: actions/upload-artifact")
release_attach_index = build_workflow.index("uses: softprops/action-gh-release")
assert_true(
    validation_index < build_index < upload_index < release_attach_index,
    "mongoose-build.yml must validate release metadata before building, uploading, or attaching release assets.",
)

github_ref_type = os.environ.get("GITHUB_REF_TYPE", "")
github_ref_name = os.environ.get("GITHUB_REF_NAME", "")
if github_ref_type == "tag" or github_ref_name.startswith("v"):
    expected_tag = f"v{version}"
    assert_true(
        github_ref_name == expected_tag,
        f"Release tag {github_ref_name!r} does not match Mongoose CLI version {expected_tag!r}.",
    )

print(f"Release version validation passed for mongoose {version}.")
