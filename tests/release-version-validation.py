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
START_RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "start-release-branch.yml"
RELEASE_ON_MERGE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-on-merge.yml"
RELEASE_SCOPE_GATES = REPO_ROOT / "docs" / "release-scope-gates.md"
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
    ".test-localappdata-mongoose-runtime",
    ".test-mongoose-fixtures",
    ".test-mongoose-runtime-fixtures",
    ".test-mongoose-registry-only-update",
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
    for root, dirs, names in os.walk(REPO_ROOT):
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_PARTS]
        for name in names:
            if name in IGNORED_PARTS:
                continue
            path = Path(root) / name
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


def branch_version(branch_name: str) -> str | None:
    match = re.fullmatch(r"release/v(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9_.-]+)?)", branch_name)
    if match is None:
        return None
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
assert_true(
    read_constant("DEFAULT_REGISTRY_URL") == "https://github.com/Nickel85/Mongoose.git",
    "DEFAULT_REGISTRY_URL must point at the public Mongoose repository.",
)
assert_true(RELEASE_SCOPE_GATES.exists(), "docs/release-scope-gates.md is missing.")

release_scope_gates = RELEASE_SCOPE_GATES.read_text(encoding="utf-8")
for required_text in (
    "## Configuration Management Strategy",
    "Start Release Branch",
    "release/v<major>.<minor>.<patch>",
    "Issue branches for that release branch from the release branch",
    "GitHub Actions validates the release branch",
    "SemVer impact and roadmap intent",
    "## v0.2.0 Exit Checklist",
    "## Milestone Start Gates",
    "## Release-Prep Issue Checklist",
    "install, update, version,",
    "release asset, and documentation loop",
    "Rollback and recovery",
):
    assert_true(
        required_text in release_scope_gates,
        f"release-scope-gates.md is missing required release gate text: {required_text}",
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
start_release_workflow = assert_workflow_runs_release_validation(START_RELEASE_WORKFLOW)
release_workflow = assert_workflow_runs_release_validation(RELEASE_ON_MERGE_WORKFLOW)

for path, workflow in (
    (MONGOOSE_BUILD_WORKFLOW, build_workflow),
    (MONGOOSE_SMOKE_WORKFLOW, smoke_workflow),
):
    assert_true(
        '"release/v*"' in workflow,
        f"{path.relative_to(REPO_ROOT)} must run for release/v* branches.",
    )

for required_text in (
    "workflow_dispatch:",
    "version:",
    "release_type:",
    "release_theme:",
    "release/v$env:RELEASE_VERSION",
    "MONGOOSE_VERSION",
    "CHANGELOG.md",
    "python ./tests/release-version-validation.py",
    "git checkout -b $branch",
    "git push origin $branch",
):
    assert_true(
        required_text in start_release_workflow,
        f"start-release-branch.yml is missing required release-start automation text: {required_text}",
    )

for required_text in (
    "types:",
    "- closed",
    "branches:",
    "- main",
    "startsWith(github.event.pull_request.head.ref, 'release/v')",
    "MONGOOSE_RELEASE_BRANCH",
    '.StartsWith("$header - ")',
    "gh release create $env:RELEASE_TAG",
    "--target main",
    "--notes-file .\\release-notes.md",
):
    assert_true(
        required_text in release_workflow,
        f"release-on-merge.yml is missing required release automation text: {required_text}",
    )

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
release_branch_name = os.environ.get("MONGOOSE_RELEASE_BRANCH", "")
if github_ref_type == "tag" or github_ref_name.startswith("v"):
    expected_tag = f"v{version}"
    assert_true(
        github_ref_name == expected_tag,
        f"Release tag {github_ref_name!r} does not match Mongoose CLI version {expected_tag!r}.",
    )

for candidate_branch in (github_ref_name, release_branch_name):
    if not candidate_branch.startswith("release/"):
        continue
    expected_branch_version = branch_version(candidate_branch)
    assert_true(
        expected_branch_version is not None,
        f"Release branch {candidate_branch!r} must be named release/v<semver>.",
    )
    assert_true(
        expected_branch_version == version,
        f"Release branch {candidate_branch!r} does not match Mongoose CLI version {version!r}.",
    )

print(f"Release version validation passed for mongoose {version}.")
